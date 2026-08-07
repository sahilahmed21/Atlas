"""RED/GREEN: thin OpenAI-compatible worker client (AC-007)."""

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
