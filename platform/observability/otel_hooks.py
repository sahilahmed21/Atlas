"""Thin OpenTelemetry hooks for the gateway request path."""

from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

from opentelemetry import trace
from opentelemetry.trace import Span


@contextmanager
def start_chat_span(
    *,
    tenant_id: str | None = None,
    strategy: str | None = None,
) -> Iterator[Span]:
    tracer = trace.get_tracer("atlas.gateway")
    with tracer.start_as_current_span("atlas.chat_completions") as span:
        if tenant_id:
            span.set_attribute("atlas.tenant_id", tenant_id)
        if strategy:
            span.set_attribute("atlas.strategy", strategy)
        yield span
