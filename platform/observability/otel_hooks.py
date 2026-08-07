"""Thin OpenTelemetry hooks for the gateway request path."""

from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

from opentelemetry import trace
from opentelemetry.trace import Span


def begin_chat_span(
    *,
    tenant_id: str | None = None,
    strategy: str | None = None,
) -> Span:
    """Start a span the caller must end (needed so streams outlive the handler)."""
    tracer = trace.get_tracer("atlas.gateway")
    span = tracer.start_span("atlas.chat_completions")
    if tenant_id:
        span.set_attribute("atlas.tenant_id", tenant_id)
    if strategy:
        span.set_attribute("atlas.strategy", strategy)
    return span


@contextmanager
def start_chat_span(
    *,
    tenant_id: str | None = None,
    strategy: str | None = None,
) -> Iterator[Span]:
    span = begin_chat_span(tenant_id=tenant_id, strategy=strategy)
    with trace.use_span(span, end_on_exit=True):
        yield span
