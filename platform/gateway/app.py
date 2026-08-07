"""FastAPI OpenAI-compatible gateway (Phase 4)."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Callable

from fastapi import FastAPI, Header
from fastapi.responses import JSONResponse, Response, StreamingResponse
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from pydantic import BaseModel

from atlas_metrics import AtlasMetrics
from openai_worker_client import OpenAIWorkerClient
from otel_hooks import start_chat_span
from rpm import RPM_SCOPE, ProcessLocalRPMLimiter
from strategies import LeastLoadRouter, build_router
from tenants import authenticate, load_tenants
from workers_registry import load_workers, resolve_workers


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


def _prompt_text(messages: list[ChatMessage]) -> str:
    return "\n".join(f"{m.role}: {m.content}" for m in messages)


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

    app = FastAPI(title="Atlas gateway", version="0.1.0")
    app.state.tenants = tenants
    app.state.workers = workers
    app.state.router_impl = router
    app.state.strategy = strategy
    app.state.loads = loads or {}
    app.state.prefix_owners = prefix_owners or {}
    app.state.metrics = metrics

    @app.get("/metrics")
    def prometheus_metrics():
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

        if not rpm.check(tenant.id, tenant.rpm_limit):
            return _error(429, "Rate limit exceeded", "rate_limit_error")

        if not body.model:
            return _error(400, "Missing required parameter: model")
        if not body.messages:
            return _error(400, "Missing required parameter: messages")

        if body.model not in tenant.allowed_models:
            return _error(403, "Model not allowed for tenant", "permission_error")

        eligible = resolve_workers(workers, body.model)
        if not eligible:
            return _error(404, f"No workers for model {body.model}", "not_found_error")

        rpm.record(tenant.id)
        metrics.queue_inc()
        t0 = time.perf_counter()
        decision = None
        worker = None
        stream_owns_queue = False

        try:
            with start_chat_span(tenant_id=tenant.id, strategy=strategy) as span:
                prompt = _prompt_text(body.messages)
                choose_kwargs: dict[str, Any] = {}
                if isinstance(router, LeastLoadRouter):
                    choose_kwargs["loads"] = app.state.loads
                if strategy == "prefix_aware":
                    choose_kwargs["prompt"] = prompt
                    choose_kwargs["prefix_owners"] = app.state.prefix_owners

                decision = router.choose(eligible, **choose_kwargs)
                worker = next(w for w in eligible if w.id == decision.worker_id)
                span.set_attribute("atlas.worker_id", worker.id)
                span.set_attribute("atlas.cache_signal", decision.cache_signal)

                client = factory(worker.base_url)
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
                    upstream = client.stream_chat_completions(payload)
                    stream_owns_queue = True

                    def event_stream():
                        outcome = "error"
                        timings: dict[str, Any] = {}
                        try:
                            for line in upstream:
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

                    return StreamingResponse(
                        event_stream(),
                        media_type="text/event-stream",
                        headers=route_headers,
                    )

                payload = {
                    "model": body.model,
                    "messages": [m.model_dump() for m in body.messages],
                    "stream": False,
                }
                upstream = client.chat_completions(payload)
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
            if decision is not None and worker is not None and not stream_owns_queue:
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
            if not stream_owns_queue:
                metrics.queue_dec()

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
