"""RED/GREEN: OTEL span hook (AC-012)."""


def test_chat_span_recorded_in_memory():
    from opentelemetry import trace
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import SimpleSpanProcessor
    from opentelemetry.sdk.trace.export.in_memory_span_exporter import (
        InMemorySpanExporter,
    )

    from otel_hooks import start_chat_span

    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    trace.set_tracer_provider(provider)

    with start_chat_span(tenant_id="demo", strategy="round_robin") as span:
        span.set_attribute("atlas.worker_id", "worker-a")

    spans = exporter.get_finished_spans()
    assert any(s.name == "atlas.chat_completions" for s in spans)
