"""FastAPI OpenAI-compatible gateway (Phase 4)."""

from __future__ import annotations

import asyncio
import inspect
import json
import logging
import os
import threading
import time
from contextlib import aclosing, asynccontextmanager
from pathlib import Path
from typing import Any, Callable

import httpx
from fastapi import FastAPI, Header, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from atlas_metrics import AtlasMetrics
from openai_worker_client import OpenAIWorkerClient
from otel_hooks import begin_chat_span, configure_tracing
from recorder import Recorder, RunClosed, Step, StepConflict
from recording import (
    fault_for,
    fault_payload,
    parse_fault_headers,
    parse_record_headers,
    sse_chunks,
    usage_from_json,
    usage_from_sse,
)
from rpm import RPM_SCOPE, ProcessLocalRPMLimiter
from strategies import LeastLoadRouter, PrefixAwareRouter, build_router, shared_prefix_key
from tenants import authenticate, load_tenants
from workers_registry import load_workers, resolve_workers

log = logging.getLogger("atlas.gateway")


def _error(
    status: int,
    message: str,
    err_type: str = "invalid_request_error",
    extra_headers: dict[str, str] | None = None,
    extra: dict[str, Any] | None = None,
) -> JSONResponse:
    headers = {"x-atlas-rpm-scope": RPM_SCOPE}
    if extra_headers:
        headers.update(extra_headers)
    return JSONResponse(
        status_code=status,
        content={"error": {"message": message, "type": err_type, **(extra or {})}},
        headers=headers,
    )


def _bearer(authorization: str | None) -> str | None:
    if not authorization:
        return None
    parts = authorization.split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None
    return parts[1].strip() or None


def _api_key(
    authorization: str | None, api_key: str | None, allow_query: bool
) -> str | None:
    """Bearer always; query api_key only when the demo flag allows it (EventSource can't set headers)."""
    bearer = _bearer(authorization)
    if bearer or not allow_query:
        return bearer
    return api_key.strip() if api_key else None


def _validate_chat_body(body: Any) -> str | None:
    """Gateway-level checks only; everything else is forwarded to the worker untouched."""
    if not isinstance(body, dict):
        return "Request body must be a JSON object"
    if not isinstance(body.get("model"), str) or not body["model"]:
        return "Missing required parameter: model"
    messages = body.get("messages")
    if not isinstance(messages, list) or not messages:
        return "Missing required parameter: messages"
    for m in messages:
        if not isinstance(m, dict) or not isinstance(m.get("role"), str):
            return "Each message must be an object with a string role"
    if "stream" in body and not isinstance(body["stream"], bool):
        return "stream must be a boolean"
    return None


def create_app(
    *,
    tenants_path: str | Path,
    workers_path: str | Path,
    strategy: str = "round_robin",
    worker_client_factory: Callable[[str], Any] | None = None,
    loads: dict[str, int] | None = None,
    prefix_owners: dict[str, str] | None = None,
    metrics: AtlasMetrics | None = None,
    load_margin: int = 0,
    allow_query_key: bool = False,
    recorder: Recorder | None = None,
    record_max_bytes: int = 8 * 1024 * 1024,
) -> FastAPI:
    tenants = load_tenants(tenants_path)
    workers = load_workers(workers_path)
    load_margin = max(0, int(load_margin))
    router = build_router(strategy, load_margin=load_margin)
    # Resolve upstream secrets once at startup; a missing variable is a deploy error, not a 502.
    upstream_keys: dict[str, str] = {}
    for w in workers:
        if w.api_key_env:
            value = os.environ.get(w.api_key_env)
            if not value:
                raise RuntimeError(
                    f"Worker {w.id} needs env var {w.api_key_env}, which is not set"
                )
            upstream_keys[w.base_url] = value
    factory = worker_client_factory or (
        lambda base_url: OpenAIWorkerClient(
            base_url=base_url, api_key=upstream_keys.get(base_url.rstrip("/"))
        )
    )
    metrics = metrics or AtlasMetrics()
    rpm = ProcessLocalRPMLimiter()
    client_cache: dict[str, Any] = {}
    cache_lock = threading.Lock()
    route_lock = threading.Lock()

    def get_client(base_url: str) -> Any:
        with cache_lock:
            if base_url not in client_cache:
                client_cache[base_url] = factory(base_url)
            return client_cache[base_url]

    def _load_inc(worker_id: str) -> None:
        with route_lock:
            app.state.loads[worker_id] = app.state.loads.get(worker_id, 0) + 1

    def _load_dec(worker_id: str) -> None:
        with route_lock:
            cur = app.state.loads.get(worker_id, 0)
            app.state.loads[worker_id] = max(0, cur - 1)

    def _claim_prefix(prefix_key: str, worker_id: str, cache_signal: str) -> None:
        if cache_signal != "miss":
            return
        with route_lock:
            # ponytail: no eviction; add LRU if unique-prefix map growth matters
            app.state.prefix_owners[prefix_key] = worker_id

    def _route_loads() -> dict[str, int]:
        """In-flight + optional soft served pressure when load gate is on."""
        with route_lock:
            out = dict(app.state.loads)
            if load_margin > 0:
                for wid, n in app.state.served_counts.items():
                    out[wid] = out.get(wid, 0) + int(n)
            return out

    def _served_inc(worker_id: str) -> None:
        if load_margin <= 0:
            return
        with route_lock:
            app.state.served_counts[worker_id] = (
                app.state.served_counts.get(worker_id, 0) + 1
            )

    def _stored_response(stored: Step, tenant_id: str, replayed: bool = True) -> Response:
        """Serve a recorded step exactly as it was sent the first time (no upstream involved)."""
        headers = {
            "x-atlas-run-id": stored.run_id,
            "x-atlas-step": str(stored.step),
            "x-atlas-worker-id": stored.worker_id or "n/a",
            "x-atlas-tenant-id": tenant_id,
            "x-atlas-rpm-scope": RPM_SCOPE,
        }
        if replayed:
            headers["x-atlas-replay"] = "1"
        metrics.observe_request(
            tenant_id=tenant_id,
            strategy="replay" if replayed else "fault",
            worker_id=stored.worker_id or "n/a",
            outcome="replayed" if replayed else "fault",
            ttft_ms=stored.ttft_ms,
            completion_ms=stored.completion_ms,
            reason=f"replay {stored.run_id}#{stored.step}",
        )
        if stored.is_stream:
            text = stored.resp_body.decode("utf-8")

            async def replay_stream():
                for chunk in sse_chunks(text):
                    yield chunk

            return StreamingResponse(
                replay_stream(),
                status_code=stored.resp_status,
                media_type="text/event-stream",
                headers=headers,
            )
        return Response(
            content=stored.resp_body,
            status_code=stored.resp_status,
            media_type="application/json",
            headers=headers,
        )

    def _recorder_failure(exc: Exception) -> JSONResponse:
        if isinstance(exc, StepConflict):
            return _error(409, str(exc), "run_step_conflict")
        if isinstance(exc, RunClosed):
            return _error(409, str(exc), "run_closed")
        metrics.recorder_error(type(exc).__name__)
        log.error("recorder failure: %s: %s", type(exc).__name__, exc)
        return _error(503, "Recorder unavailable", "recorder_unavailable")

    async def _serve_recorded(tenant_id: str, ctx: Any) -> Response | None:
        """Replay a stored step, or (record mode) dedupe a retry. None = go to the worker."""
        try:
            stored = await recorder.get_step(tenant_id, ctx.run_id, ctx.step)
            if stored is None:
                if ctx.mode == "record":
                    return None
                run = await recorder.get_run(tenant_id, ctx.run_id)
                return _error(
                    404,
                    "No recorded step for this run",
                    "replay_step_missing",
                    extra={
                        "run_id": ctx.run_id,
                        "step": ctx.step,
                        "run_status": run["status"] if run else None,
                    },
                )
            if stored.req_hash != ctx.req_hash:
                if ctx.mode == "record":
                    return _error(
                        409,
                        "Step already recorded with a different request",
                        "run_step_conflict",
                    )
                return _error(
                    409,
                    "Request differs from the recorded step",
                    "replay_divergence",
                    extra={
                        "step": ctx.step,
                        "expected_hash": stored.req_hash,
                        "actual_hash": ctx.req_hash,
                    },
                )
            return _stored_response(stored, tenant_id)
        except Exception as exc:  # converted to a 503 + metric + log, never swallowed
            return _recorder_failure(exc)

    async def _commit(
        tenant_id: str,
        ctx: Any,
        *,
        status: int,
        body: bytes,
        is_stream: bool,
        worker_id: str,
        stats: dict[str, Any],
        outcome: str,
        usage: tuple[int | None, int | None],
        fault: str | None = None,
    ) -> Step:
        return await recorder.commit_step(
            Step(
                tenant_id=tenant_id,
                run_id=ctx.run_id,
                step=ctx.step,
                req_hash=ctx.req_hash,
                req_body=ctx.req_body,
                resp_status=status,
                resp_body=body,
                is_stream=is_stream,
                worker_id=worker_id,
                ttft_ms=stats.get("ttft_ms"),
                completion_ms=stats.get("completion_ms"),
                prompt_tokens=usage[0],
                completion_tokens=usage[1],
                fault=fault,
                outcome=outcome,
                ts=time.time(),
            )
        )

    async def _inject_fault(tenant_id: str, ctx: Any, kind: str, stream: bool) -> Response:
        """Answer with a synthetic failure; it is recorded as the step's result like any other."""
        status, payload, is_sse = fault_payload(kind, stream)
        try:
            stored = await _commit(
                tenant_id, ctx, status=status, body=payload, is_stream=is_sse,
                worker_id="fault", stats={}, outcome="fault", usage=(None, None), fault=kind,
            )
        except Exception as exc:
            return _recorder_failure(exc)
        return _stored_response(stored, tenant_id, replayed=False)

    def _flag_incomplete(tenant_id: str, run_id: str) -> None:
        """Mark a run whose step could not be stored; sync so it is safe during cancellation."""
        try:
            recorder.mark_incomplete(tenant_id, run_id)
        except Exception as exc:
            metrics.recorder_error(type(exc).__name__)
            log.error("could not flag run %s incomplete: %s", run_id, exc)

    async def _commit_stream(
        tenant_id: str,
        ctx: Any,
        buffered: list[str],
        overflow: bool,
        worker_id: str,
        stats: dict[str, Any],
        outcome: str,
    ) -> bool:
        """Store a finished (or truncated) stream. False = the run must be flagged incomplete."""
        if overflow:
            metrics.recorder_error("stream_too_large")
            log.warning("stream for run %s exceeded %d bytes; not recorded", ctx.run_id, record_max_bytes)
            return False
        text = "".join(buffered)
        try:
            await _commit(
                tenant_id, ctx, status=200, body=text.encode("utf-8"), is_stream=True,
                worker_id=worker_id, stats=stats, outcome=outcome, usage=usage_from_sse(text),
            )
            return True
        except Exception as exc:
            _recorder_failure(exc)  # metric + log; the 200 response is already on the wire
            return False

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        yield
        if recorder is not None:
            recorder.close()
        with cache_lock:
            for c in client_cache.values():
                close = getattr(c, "close", None)
                if close is None:
                    continue
                result = close()
                if inspect.isawaitable(result):
                    await result

    app = FastAPI(title="Atlas gateway", version="0.1.0", lifespan=lifespan)
    app.state.tenants = tenants
    app.state.workers = workers
    app.state.router_impl = router
    app.state.strategy = strategy
    app.state.loads = loads or {}
    app.state.prefix_owners = prefix_owners or {}
    app.state.metrics = metrics
    app.state.load_margin = load_margin
    app.state.served_counts = {}

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(request: Request, exc: RequestValidationError):
        return _error(400, "Invalid request body", "invalid_request_error")

    @app.get("/metrics")
    def prometheus_metrics(authorization: str | None = Header(default=None)):
        if authenticate(tenants, _bearer(authorization)) is None:
            return _error(401, "Invalid API key", "authentication_error")
        return Response(
            content=generate_latest(metrics.registry),
            media_type=CONTENT_TYPE_LATEST,
        )

    @app.get("/atlas/snapshot")
    def atlas_snapshot(
        authorization: str | None = Header(default=None),
        api_key: str | None = Query(default=None),
        limit: int = Query(default=50, ge=1, le=500),
        after: int = Query(default=0, ge=0),
    ):
        tenant = authenticate(tenants, _api_key(authorization, api_key, allow_query_key))
        if tenant is None:
            return _error(401, "Invalid API key", "authentication_error")
        return {
            "events": metrics.events.snapshot(
                limit=limit, after=after, tenant_id=tenant.id
            ),
            "scope": "process-local",
        }

    @app.get("/atlas/events")
    async def atlas_events(
        authorization: str | None = Header(default=None),
        api_key: str | None = Query(default=None),
        after: int = Query(default=0, ge=0),
        catchup_only: bool = Query(default=False),
    ):
        tenant = authenticate(tenants, _api_key(authorization, api_key, allow_query_key))
        if tenant is None:
            return _error(401, "Invalid API key", "authentication_error")

        async def event_feed():
            cursor = after
            for row in metrics.events.snapshot(
                limit=200, after=cursor, tenant_id=tenant.id
            ):
                cursor = int(row["id"])
                yield f"data: {json.dumps(row)}\n\n"
            if catchup_only:
                return
            while True:
                newer = await asyncio.to_thread(
                    lambda c=cursor: metrics.events.wait_after(
                        c, timeout=1.0, tenant_id=tenant.id
                    )
                )
                if not newer:
                    yield ": ping\n\n"
                    continue
                for ev in newer:
                    cursor = ev.id
                    yield f"data: {json.dumps(ev.as_public_dict())}\n\n"

        return StreamingResponse(event_feed(), media_type="text/event-stream")

    def _run_access(authorization: str | None):
        """(tenant, None) or (None, error response) for the run API."""
        tenant = authenticate(tenants, _bearer(authorization))
        if tenant is None:
            return None, _error(401, "Invalid API key", "authentication_error")
        if recorder is None:
            return None, _error(
                400, "Recording is not enabled on this gateway", "recording_disabled"
            )
        if not tenant.record_allowed:
            return None, _error(403, "Tenant may not use recorded runs", "permission_error")
        return tenant, None

    @app.post("/atlas/runs/{run_id:path}/end")
    async def end_run(run_id: str, authorization: str | None = Header(default=None)):
        tenant, err = _run_access(authorization)
        if err is not None:
            return err
        try:
            status = await recorder.close_run(tenant.id, run_id)
        except Exception as exc:
            return _recorder_failure(exc)
        if status is None:
            return _error(404, "Run not found", "not_found_error")
        return {"run_id": run_id, "status": status}

    @app.get("/atlas/runs/{run_id:path}")
    async def get_run(run_id: str, authorization: str | None = Header(default=None)):
        tenant, err = _run_access(authorization)
        if err is not None:
            return err
        try:
            run = await recorder.get_run(tenant.id, run_id)
        except Exception as exc:
            return _recorder_failure(exc)
        if run is None:
            return _error(404, "Run not found", "not_found_error")
        return run

    @app.post("/v1/chat/completions")
    async def chat_completions(
        request: Request,
        authorization: str | None = Header(default=None),
    ):
        tenant = authenticate(tenants, _bearer(authorization))
        if tenant is None:
            return _error(401, "Invalid API key", "authentication_error")

        try:
            body = await request.json()
        except ValueError:
            return _error(400, "Invalid request body")
        problem = _validate_chat_body(body)
        if problem:
            return _error(400, problem)
        model = body["model"]

        if model not in tenant.allowed_models:
            return _error(403, "Model not allowed for tenant", "permission_error")

        ctx, problem = parse_record_headers(request.headers, body)
        fault_plan, fault_problem = parse_fault_headers(request.headers)
        problem = problem or fault_problem
        if not problem and fault_plan is not None and ctx is None:
            problem = "Fault injection requires x-atlas-mode: record"
        if problem:
            return _error(400, problem)
        if ctx is not None:
            if recorder is None:
                return _error(
                    400, "Recording is not enabled on this gateway", "recording_disabled"
                )
            if not tenant.record_allowed:
                return _error(
                    403, "Tenant may not record or replay runs", "permission_error"
                )
            served = await _serve_recorded(tenant.id, ctx)
            if served is not None:
                return served
            if fault_plan is not None and ctx.mode == "record":
                kind = fault_for(fault_plan.seed, ctx.step, fault_plan.rate)
                if kind is not None:
                    return await _inject_fault(
                        tenant.id, ctx, kind, body.get("stream") is True
                    )

        eligible = resolve_workers(workers, model)
        if not eligible:
            return _error(404, f"No workers for model {model}", "not_found_error")

        if not rpm.try_acquire(tenant.id, tenant.rpm_limit):
            return _error(429, "Rate limit exceeded", "rate_limit_error")

        t0 = time.perf_counter()
        decision = None
        worker = None
        # Span is never made "current": it outlives this task when streaming, and
        # attaching/detaching a context across tasks raises in OpenTelemetry.
        span = begin_chat_span(tenant_id=tenant.id, strategy=strategy)
        stream_owns_cleanup = False

        try:
            prefix_key = shared_prefix_key(body["messages"])
            choose_kwargs: dict[str, Any] = {}
            if isinstance(router, LeastLoadRouter):
                choose_kwargs["loads"] = app.state.loads
            if isinstance(router, PrefixAwareRouter):
                choose_kwargs["prefix_key"] = prefix_key
                choose_kwargs["prefix_owners"] = app.state.prefix_owners
                choose_kwargs["loads"] = _route_loads()

            decision = router.choose(eligible, **choose_kwargs)
            worker = next(w for w in eligible if w.id == decision.worker_id)
            _claim_prefix(prefix_key, worker.id, decision.cache_signal)
            _served_inc(worker.id)
            _load_inc(worker.id)
            span.set_attribute("atlas.worker_id", worker.id)
            span.set_attribute("atlas.cache_signal", decision.cache_signal)

            client = get_client(worker.base_url)
            route_headers = {
                "x-atlas-worker-id": decision.worker_id,
                "x-atlas-route-strategy": decision.strategy,
                "x-atlas-route-reason": decision.reason,
                "x-atlas-tenant-id": tenant.id,
                "x-atlas-rpm-scope": RPM_SCOPE,
                "x-atlas-cache-signal": decision.cache_signal,
            }

            # The worker receives the client's body exactly as sent (tools, tool_calls, ...).
            payload = body
            stats: dict[str, Any] = {}

            if body.get("stream") is True:
                stream_owns_cleanup = True

                async def event_stream():
                    # "aborted" stays only if the client disconnects mid-stream.
                    outcome = "aborted"
                    buffered: list[str] = []
                    buffered_bytes = 0
                    overflow = False
                    step_stored = False
                    metrics.queue_inc()
                    try:
                        async with aclosing(
                            client.stream_chat_completions(payload, stats)
                        ) as lines:
                            async for line in lines:
                                if ctx is not None and not overflow:
                                    buffered_bytes += len(line.encode("utf-8"))
                                    if buffered_bytes > record_max_bytes:
                                        overflow = True
                                        buffered.clear()
                                    else:
                                        buffered.append(line)
                                yield line
                        outcome = stats.get("status", "ok")
                        if ctx is not None:
                            step_stored = await _commit_stream(
                                tenant.id, ctx, buffered, overflow, worker.id, stats, outcome
                            )
                    except Exception:
                        outcome = "error"
                        if ctx is not None:  # a truncated upstream stream is still the step's result
                            step_stored = await _commit_stream(
                                tenant.id, ctx, buffered, overflow, worker.id, stats, outcome
                            )
                        raise
                    finally:
                        if ctx is not None and not step_stored:
                            _flag_incomplete(tenant.id, ctx.run_id)
                        metrics.observe_request(
                            tenant_id=tenant.id,
                            strategy=decision.strategy,
                            worker_id=decision.worker_id,
                            outcome=outcome,
                            cache_signal=decision.cache_signal,
                            ttft_ms=stats.get("ttft_ms"),
                            completion_ms=stats.get("completion_ms"),
                            tokens_per_s=stats.get("tokens_per_s"),
                            reason=decision.reason,
                        )
                        metrics.queue_dec()
                        _load_dec(worker.id)
                        span.set_attribute("atlas.outcome", outcome)
                        span.end()

                return StreamingResponse(
                    event_stream(),
                    media_type="text/event-stream",
                    headers=route_headers,
                )

            metrics.queue_inc()
            try:
                upstream = await client.chat_completions(payload, stats)
            except (httpx.HTTPError, ValueError) as exc:
                metrics.observe_request(
                    tenant_id=tenant.id,
                    strategy=decision.strategy,
                    worker_id=decision.worker_id,
                    outcome="error",
                    cache_signal=decision.cache_signal,
                    completion_ms=(time.perf_counter() - t0) * 1000,
                    reason=decision.reason,
                )
                span.set_attribute("atlas.outcome", "error")
                msg = "Worker request failed"
                if isinstance(exc, httpx.HTTPStatusError):
                    msg = f"Worker error: {exc.response.status_code}"
                err = _error(502, msg, "upstream_error", extra_headers=route_headers)
                if ctx is not None:
                    # An upstream failure is a legitimate step result: record it so replay matches.
                    try:
                        await _commit(
                            tenant.id, ctx, status=502, body=err.body, is_stream=False,
                            worker_id=worker.id, stats=stats, outcome="error",
                            usage=(None, None),
                        )
                    except Exception as commit_exc:
                        return _recorder_failure(commit_exc)
                    err.headers["x-atlas-run-id"] = ctx.run_id
                    err.headers["x-atlas-step"] = str(ctx.step)
                return err

            if stats.get("completion_ms") is None:
                stats["completion_ms"] = (time.perf_counter() - t0) * 1000
            span.set_attribute("atlas.outcome", stats.get("status", "ok"))
            metrics.observe_request(
                tenant_id=tenant.id,
                strategy=decision.strategy,
                worker_id=decision.worker_id,
                outcome=stats.get("status", "ok"),
                cache_signal=decision.cache_signal,
                ttft_ms=stats.get("ttft_ms"),
                completion_ms=stats.get("completion_ms"),
                tokens_per_s=stats.get("tokens_per_s"),
                reason=decision.reason,
            )
            resp = JSONResponse(content=upstream, headers=route_headers)
            if ctx is not None:
                try:
                    stored = await _commit(
                        tenant.id, ctx, status=200, body=resp.body, is_stream=False,
                        worker_id=worker.id, stats=stats,
                        outcome=stats.get("status", "ok"), usage=usage_from_json(upstream),
                    )
                except Exception as commit_exc:
                    return _recorder_failure(commit_exc)
                if stored.resp_body != resp.body:  # lost a race: answer with the winner's bytes
                    return _stored_response(stored, tenant.id)
                resp.headers["x-atlas-run-id"] = ctx.run_id
                resp.headers["x-atlas-step"] = str(ctx.step)
            return resp
        except Exception:
            if (
                decision is not None
                and worker is not None
                and not stream_owns_cleanup
            ):
                metrics.observe_request(
                    tenant_id=tenant.id,
                    strategy=decision.strategy,
                    worker_id=decision.worker_id,
                    outcome="error",
                    cache_signal=decision.cache_signal,
                    completion_ms=(time.perf_counter() - t0) * 1000,
                    reason=decision.reason,
                )
            raise
        finally:
            if not stream_owns_cleanup:
                if worker is not None:
                    _load_dec(worker.id)
                metrics.queue_dec()
                span.end()

    @app.get("/healthz")
    async def healthz():
        return {"status": "ok"}

    dash_dir = Path(__file__).resolve().parents[2] / "dashboard"
    if dash_dir.is_dir():
        app.mount(
            "/dashboard",
            StaticFiles(directory=str(dash_dir), html=True),
            name="dashboard",
        )

    return app


def create_app_from_env() -> FastAPI:
    """Uvicorn entry: ATLAS_TENANTS / ATLAS_WORKERS / ATLAS_STRATEGY / ATLAS_PREFIX_LOAD_MARGIN."""
    import os

    root = Path(__file__).resolve().parents[2]
    tenants = os.environ.get("ATLAS_TENANTS", str(root / "configs/tenants/example.yaml"))
    workers = os.environ.get("ATLAS_WORKERS", str(root / "configs/models/workers.yaml"))
    strategy = os.environ.get("ATLAS_STRATEGY", "round_robin")
    margin = int(os.environ.get("ATLAS_PREFIX_LOAD_MARGIN", "0"))
    # Demo only: the dashboard's EventSource cannot send an Authorization header.
    allow_query_key = os.environ.get("ATLAS_ALLOW_QUERY_KEY") == "1"
    configure_tracing()  # env-driven: OTLP endpoint, console, or off
    db_path = os.environ.get("ATLAS_RECORDER_DB")
    return create_app(
        tenants_path=tenants,
        workers_path=workers,
        strategy=strategy,
        load_margin=margin,
        allow_query_key=allow_query_key,
        recorder=Recorder(db_path) if db_path else None,
        record_max_bytes=int(os.environ.get("ATLAS_RECORD_MAX_BYTES", 8 * 1024 * 1024)),
    )
