"""Thin OpenTelemetry hooks for the gateway request path."""

from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Iterator

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import (
    BatchSpanProcessor,
    ConsoleSpanExporter,
    SimpleSpanProcessor,
    SpanExporter,
)
from opentelemetry.trace import Span

# Gateway-owned provider; never installed globally so tests and apps can swap it freely.
_provider: TracerProvider | None = None


def configure_tracing(exporter: SpanExporter | None = None) -> TracerProvider | None:
    """Install (or clear) the gateway's tracer provider.

    An explicit exporter is exported synchronously (tests). Otherwise the env decides:
    OTEL_EXPORTER_OTLP_ENDPOINT -> OTLP/HTTP, ATLAS_OTEL_CONSOLE=1 -> stdout, else tracing is off.
    """
    global _provider
    if exporter is not None:
        processor = SimpleSpanProcessor(exporter)
    elif os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT"):
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

        processor = BatchSpanProcessor(OTLPSpanExporter())
    elif os.environ.get("ATLAS_OTEL_CONSOLE") == "1":
        processor = BatchSpanProcessor(ConsoleSpanExporter())
    else:
        _provider = None
        return None
    provider = TracerProvider()
    provider.add_span_processor(processor)
    _provider = provider
    return provider


def begin_chat_span(
    *,
    tenant_id: str | None = None,
    strategy: str | None = None,
) -> Span:
    """Start a span the caller must end (needed so streams outlive the handler)."""
    tracer = (_provider or trace.get_tracer_provider()).get_tracer("atlas.gateway")
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
