"""FastAPI OpenAI-compatible gateway (Phase 4 scaffolding)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

from fastapi import FastAPI, Header
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel

from openai_worker_client import OpenAIWorkerClient
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


def _error(status: int, message: str, err_type: str = "invalid_request_error") -> JSONResponse:
    return JSONResponse(
        status_code=status,
        content={"error": {"message": message, "type": err_type}},
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
) -> FastAPI:
    tenants = load_tenants(tenants_path)
    workers = load_workers(workers_path)
    router = build_router(strategy)
    factory = worker_client_factory or (
        lambda base_url: OpenAIWorkerClient(base_url=base_url)
    )

    app = FastAPI(title="Atlas gateway", version="0.1.0")
    app.state.tenants = tenants
    app.state.workers = workers
    app.state.router_impl = router
    app.state.strategy = strategy
    app.state.loads = loads or {}
    app.state.prefix_owners = prefix_owners or {}

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
            return _error(403, f"Model not allowed for tenant", "permission_error")

        eligible = resolve_workers(workers, body.model)
        if not eligible:
            return _error(404, f"No workers for model {body.model}", "not_found_error")

        prompt = _prompt_text(body.messages)
        choose_kwargs: dict[str, Any] = {}
        if isinstance(router, LeastLoadRouter):
            choose_kwargs["loads"] = app.state.loads
        if strategy == "prefix_aware":
            choose_kwargs["prompt"] = prompt
            choose_kwargs["prefix_owners"] = app.state.prefix_owners

        decision = router.choose(eligible, **choose_kwargs)
        worker = next(w for w in eligible if w.id == decision.worker_id)
        client = factory(worker.base_url)

        payload = {
            "model": body.model,
            "messages": [m.model_dump() for m in body.messages],
            "stream": False,
        }
        upstream = client.chat_completions(payload)

        headers = {
            "x-atlas-worker-id": decision.worker_id,
            "x-atlas-route-strategy": decision.strategy,
            "x-atlas-route-reason": decision.reason,
            "x-atlas-tenant-id": tenant.id,
        }

        if not body.stream:
            return JSONResponse(content=upstream, headers=headers)

        # Scaffold SSE: one content chunk from fake/upstream non-stream body.
        content = ""
        try:
            content = upstream["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError):
            content = ""

        def event_stream():
            chunk = {
                "id": upstream.get("id", "chatcmpl-atlas"),
                "object": "chat.completion.chunk",
                "model": body.model,
                "choices": [
                    {
                        "index": 0,
                        "delta": {"role": "assistant", "content": content},
                        "finish_reason": "stop",
                    }
                ],
            }
            yield f"data: {json.dumps(chunk)}\n\n"
            yield "data: [DONE]\n\n"

        return StreamingResponse(
            event_stream(),
            media_type="text/event-stream",
            headers=headers,
        )

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
