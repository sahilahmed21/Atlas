"""RED/GREEN: thin OpenAI-compatible worker client (AC-007, AC-009)."""

import json
import time

import httpx
import pytest


def test_chat_completions_posts_to_v1_path():
    from openai_worker_client import OpenAIWorkerClient

    calls: list[tuple[str, str]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append((request.method, str(request.url)))
        return httpx.Response(
            200,
            json={
                "id": "chatcmpl-fake",
                "object": "chat.completion",
                "choices": [
                    {
                        "index": 0,
                        "message": {"role": "assistant", "content": "pong"},
                        "finish_reason": "stop",
                    }
                ],
            },
        )

    transport = httpx.MockTransport(handler)
    http = httpx.Client(transport=transport, base_url="http://worker.test/v1")
    client = OpenAIWorkerClient(base_url="http://worker.test/v1", http=http)

    body = client.chat_completions(
        {
            "model": "Qwen/Qwen2.5-0.5B-Instruct",
            "messages": [{"role": "user", "content": "ping"}],
        }
    )

    assert body["choices"][0]["message"]["content"] == "pong"
    assert len(calls) == 1
    assert calls[0][0] == "POST"
    assert calls[0][1].endswith("/v1/chat/completions")


def test_chat_completions_raises_on_http_error():
    from openai_worker_client import OpenAIWorkerClient

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, json={"error": {"message": "down"}})

    http = httpx.Client(
        transport=httpx.MockTransport(handler),
        base_url="http://worker.test/v1",
    )
    client = OpenAIWorkerClient(base_url="http://worker.test/v1", http=http)

    with pytest.raises(httpx.HTTPStatusError):
        client.chat_completions(
            {"model": "m", "messages": [{"role": "user", "content": "x"}]}
        )


def test_stream_chat_completions_records_ttft_and_request_id():
    from openai_worker_client import OpenAIWorkerClient

    chunks = [
        b'data: {"id":"chatcmpl-stream","choices":[{"delta":{"content":"a"}}]}\n\n',
        b'data: {"id":"chatcmpl-stream","choices":[{"delta":{"content":"b"},"finish_reason":"stop"}]}\n\n',
        b"data: [DONE]\n\n",
    ]

    def handler(request: httpx.Request) -> httpx.Response:
        assert json.loads(request.content)["stream"] is True
        return httpx.Response(
            200,
            content=b"".join(chunks),
            headers={"content-type": "text/event-stream"},
        )

    http = httpx.Client(
        transport=httpx.MockTransport(handler),
        base_url="http://worker.test/v1",
    )
    client = OpenAIWorkerClient(base_url="http://worker.test/v1", http=http)

    t0 = time.perf_counter()
    lines = list(
        client.stream_chat_completions(
            {
                "model": "m",
                "messages": [{"role": "user", "content": "x"}],
                "stream": True,
            }
        )
    )
    elapsed_ms = (time.perf_counter() - t0) * 1000

    assert any("chatcmpl-stream" in line for line in lines)
    assert any("[DONE]" in line for line in lines)
    timings = client.last_timings
    assert timings["status"] == "ok"
    assert timings["request_id"] == "chatcmpl-stream"
    assert timings["ttft_ms"] is not None
    assert timings["ttft_ms"] <= timings["completion_ms"]
    assert timings["completion_ms"] <= elapsed_ms + 50
