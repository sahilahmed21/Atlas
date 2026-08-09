"""FastAPI OpenAI-compatible gateway (Phase 4)."""

from __future__ import annotations

import asyncio
import inspect
import threading
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, AsyncIterator, Callable

import httpx
from fastapi import FastAPI, Header, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response, StreamingResponse
from opentelemetry import trace
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from pydantic import BaseModel

from atlas_metrics import AtlasMetrics
from openai_worker_client import OpenAIWorkerClient
from otel_hooks import begin_chat_span
from rpm import RPM_SCOPE, ProcessLocalRPMLimiter
from strategies import LeastLoadRouter, PrefixAwareRouter, build_router, shared_prefix_key
from tenants import authenticate, load_tenants
from workers_registry import load_workers, resolve_workers

_SENTINEL = object()


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatCompletionRequest(BaseModel):
    model: str | None = None
    messages: list[ChatMessage] | None = None
    stream: bool = False


def _error(
    status: int,
    message: str,
    err_type: str = "invalid_request_error",
    extra_headers: dict[str, str] | None = None,
) -> JSONResponse:
    headers = {"x-atlas-rpm-scope": RPM_SCOPE}
    if extra_headers:
        headers.update(extra_headers)
    return JSONResponse(
        status_code=status,
        content={"error": {"message": message, "type": err_type}},
        headers=headers,
    )


def _bearer(authorization: str | None) -> str | None:
    if not authorization:
        return None
    parts = authorization.split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None
    return parts[1].strip() or None


async def _call_chat(client: Any, payload: dict[str, Any]) -> dict[str, Any]:
    fn = client.chat_completions
    if inspect.iscoroutinefunction(fn):
        return await fn(payload)
    return await asyncio.to_thread(fn, payload)


async def _aiter_sse(client: Any, payload: dict[str, Any]) -> AsyncIterator[str]:
    gen = client.stream_chat_completions(payload)
    if inspect.isasyncgen(gen) or hasattr(gen, "__aiter__"):
        async for line in gen:
            yield line
        return
    it = iter(gen)

    def _next():
        return next(it, _SENTINEL)

    while True:
        line = await asyncio.to_thread(_next)
        if line is _SENTINEL:
            break
        yield line  # type: ignore[misc]


def create_app(
    *,
    tenants_path: str | Path,
    workers_path: str | Path,
    strategy: str = "round_robin",
    worker_client_factory: Callable[[str], Any] | None = None,
    loads: dict[str, int] | None = None,
    prefix_owners: dict[str, str] | None = None,
    metrics: AtlasMetrics | None = None,
) -> FastAPI:
    tenants = load_tenants(tenants_path)
    workers = load_workers(workers_path)
    router = build_router(strategy)
    factory = worker_client_factory or (
        lambda base_url: OpenAIWorkerClient(base_url=base_url)
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

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        yield
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

    @app.post("/v1/chat/completions")
    async def chat_completions(
        body: ChatCompletionRequest,
        authorization: str | None = Header(default=None),
    ):
        tenant = authenticate(tenants, _bearer(authorization))
        if tenant is None:
            return _error(401, "Invalid API key", "authentication_error")

        if not body.model:
            return _error(400, "Missing required parameter: model")
        if not body.messages:
            return _error(400, "Missing required parameter: messages")

        if body.model not in tenant.allowed_models:
            return _error(403, "Model not allowed for tenant", "permission_error")

        eligible = resolve_workers(workers, body.model)
        if not eligible:
            return _error(404, f"No workers for model {body.model}", "not_found_error")

        if not rpm.try_acquire(tenant.id, tenant.rpm_limit):
            return _error(429, "Rate limit exceeded", "rate_limit_error")

        t0 = time.perf_counter()
        decision = None
        worker = None
        span = begin_chat_span(tenant_id=tenant.id, strategy=strategy)
        span_ctx = trace.use_span(span, end_on_exit=False)
        span_ctx.__enter__()
        stream_owns_cleanup = False

        try:
            prefix_key = shared_prefix_key(body.messages)
            choose_kwargs: dict[str, Any] = {}
            if isinstance(router, LeastLoadRouter):
                choose_kwargs["loads"] = app.state.loads
            if isinstance(router, PrefixAwareRouter):
                choose_kwargs["prefix_key"] = prefix_key
                choose_kwargs["prefix_owners"] = app.state.prefix_owners
                choose_kwargs["loads"] = app.state.loads

            decision = router.choose(eligible, **choose_kwargs)
            worker = next(w for w in eligible if w.id == decision.worker_id)
            _claim_prefix(prefix_key, worker.id, decision.cache_signal)
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

            if body.stream:
                payload = {
                    "model": body.model,
                    "messages": [m.model_dump() for m in body.messages],
                    "stream": True,
                }
                stream_owns_cleanup = True

                async def event_stream():
                    outcome = "error"
                    timings: dict[str, Any] = {}
                    metrics.queue_inc()
                    try:
                        async for line in _aiter_sse(client, payload):
                            yield line
                        timings = getattr(client, "last_timings", {}) or {}
                        outcome = timings.get("status", "ok")
                    except Exception:
                        timings = getattr(client, "last_timings", {}) or {}
                        outcome = "error"
                        raise
                    finally:
                        metrics.observe_request(
                            tenant_id=tenant.id,
                            strategy=decision.strategy,
                            worker_id=decision.worker_id,
                            outcome=outcome,
                            cache_signal=decision.cache_signal,
                            ttft_ms=timings.get("ttft_ms"),
                            completion_ms=timings.get("completion_ms"),
                            tokens_per_s=timings.get("tokens_per_s"),
                        )
                        metrics.queue_dec()
                        _load_dec(worker.id)
                        span.end()
                        span_ctx.__exit__(None, None, None)

                return StreamingResponse(
                    event_stream(),
                    media_type="text/event-stream",
                    headers=route_headers,
                )

            metrics.queue_inc()
            payload = {
                "model": body.model,
                "messages": [m.model_dump() for m in body.messages],
                "stream": False,
            }
            try:
                upstream = await _call_chat(client, payload)
            except httpx.HTTPError as exc:
                metrics.observe_request(
                    tenant_id=tenant.id,
                    strategy=decision.strategy,
                    worker_id=decision.worker_id,
                    outcome="error",
                    cache_signal=decision.cache_signal,
                    completion_ms=(time.perf_counter() - t0) * 1000,
                )
                msg = "Worker request failed"
                if isinstance(exc, httpx.HTTPStatusError):
                    msg = f"Worker error: {exc.response.status_code}"
                return _error(502, msg, "upstream_error", extra_headers=route_headers)

            timings = getattr(client, "last_timings", {}) or {}
            if timings.get("completion_ms") is None:
                timings["completion_ms"] = (time.perf_counter() - t0) * 1000
            outcome = timings.get("status", "ok")
            metrics.observe_request(
                tenant_id=tenant.id,
                strategy=decision.strategy,
                worker_id=decision.worker_id,
                outcome=outcome,
                cache_signal=decision.cache_signal,
                ttft_ms=timings.get("ttft_ms"),
                completion_ms=timings.get("completion_ms"),
                tokens_per_s=timings.get("tokens_per_s"),
            )
            return JSONResponse(content=upstream, headers=route_headers)
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
                )
            raise
        finally:
            if not stream_owns_cleanup:
                if worker is not None:
                    _load_dec(worker.id)
                metrics.queue_dec()
                span.end()
                span_ctx.__exit__(None, None, None)

    @app.get("/healthz")
    async def healthz():
        return {"status": "ok"}

    return app


def create_app_from_env() -> FastAPI:
    """Uvicorn entry: ATLAS_TENANTS / ATLAS_WORKERS / ATLAS_STRATEGY."""
    import os

    root = Path(__file__).resolve().parents[2]
    tenants = os.environ.get("ATLAS_TENANTS", str(root / "configs/tenants/example.yaml"))
    workers = os.environ.get("ATLAS_WORKERS", str(root / "configs/models/workers.yaml"))
    strategy = os.environ.get("ATLAS_STRATEGY", "round_robin")
    return create_app(tenants_path=tenants, workers_path=workers, strategy=strategy)
