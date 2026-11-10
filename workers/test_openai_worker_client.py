"""RED/GREEN: async OpenAI-compatible worker client with per-call stats (AC-007, AC-009, Phase 11)."""

import asyncio
import json

import httpx
import pytest

BASE = "http://worker.test/v1"


def _client(handler):
    from openai_worker_client import OpenAIWorkerClient

    http = httpx.AsyncClient(transport=httpx.MockTransport(handler), base_url=BASE)
    return OpenAIWorkerClient(base_url=BASE, http=http)


def _sse(*events: dict | str) -> bytes:
    out = b""
    for ev in events:
        data = ev if isinstance(ev, str) else json.dumps(ev)
        out += f"data: {data}\n\n".encode()
    return out


def test_chat_completions_posts_to_v1_path_and_forwards_payload_verbatim():
    calls: list[tuple[str, str, dict]] = []
    tools = [{"type": "function", "function": {"name": "sql", "parameters": {}}}]

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append((request.method, str(request.url), json.loads(request.content)))
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
                "usage": {"completion_tokens": 4},
            },
        )

    client = _client(handler)
    stats: dict = {}
    payload = {
        "model": "m",
        "messages": [{"role": "user", "content": "ping"}],
        "tools": tools,
        "temperature": 0,
    }
    body = asyncio.run(client.chat_completions(payload, stats))

    assert body["choices"][0]["message"]["content"] == "pong"
    assert calls[0][0] == "POST"
    assert calls[0][1].endswith("/v1/chat/completions")
    assert calls[0][2] == payload
    assert stats["status"] == "ok"
    assert stats["request_id"] == "chatcmpl-fake"
    assert stats["ttft_ms"] is None
    assert stats["completion_ms"] > 0
    assert stats["tokens_per_s"] > 0


def test_api_key_is_sent_as_bearer_only_when_configured():
    from openai_worker_client import OpenAIWorkerClient

    seen: list[str | None] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request.headers.get("authorization"))
        return httpx.Response(200, json={"id": "x", "choices": []})

    def build(api_key):
        http = httpx.AsyncClient(transport=httpx.MockTransport(handler), base_url=BASE)
        return OpenAIWorkerClient(base_url=BASE, http=http, api_key=api_key)

    payload = {"model": "m", "messages": [{"role": "user", "content": "x"}]}
    asyncio.run(build("sk-upstream").chat_completions(payload, {}))
    asyncio.run(build(None).chat_completions(payload, {}))

    assert seen == ["Bearer sk-upstream", None]


def test_chat_completions_raises_on_http_error_and_marks_stats():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, json={"error": {"message": "down"}})

    client = _client(handler)
    stats: dict = {}
    with pytest.raises(httpx.HTTPStatusError):
        asyncio.run(
            client.chat_completions(
                {"model": "m", "messages": [{"role": "user", "content": "x"}]}, stats
            )
        )
    assert stats["status"] == "error"
    assert stats["completion_ms"] is not None


def test_stream_ttft_is_first_content_chunk_not_role_only_chunk():
    class SlowBody(httpx.AsyncByteStream):
        async def __aiter__(self):
            yield _sse({"id": "chatcmpl-s", "choices": [{"delta": {"role": "assistant"}}]})
            await asyncio.sleep(0.06)
            yield _sse({"id": "chatcmpl-s", "choices": [{"delta": {"content": "a"}}]})
            yield _sse({"id": "chatcmpl-s", "choices": [{"delta": {}, "finish_reason": "stop"}]})
            yield _sse("[DONE]")

    def handler(request: httpx.Request) -> httpx.Response:
        assert json.loads(request.content)["stream"] is True
        return httpx.Response(
            200, stream=SlowBody(), headers={"content-type": "text/event-stream"}
        )

    client = _client(handler)
    stats: dict = {}

    async def run() -> list[str]:
        return [
            line
            async for line in client.stream_chat_completions(
                {"model": "m", "messages": [{"role": "user", "content": "x"}], "stream": True},
                stats,
            )
        ]

    lines = asyncio.run(run())

    assert any("chatcmpl-s" in line for line in lines)
    assert any("[DONE]" in line for line in lines)
    assert all(line.endswith("\n\n") for line in lines)
    assert stats["status"] == "ok"
    assert stats["request_id"] == "chatcmpl-s"
    assert stats["ttft_ms"] >= 50  # role-only chunk arrived ~60ms before content
    assert stats["ttft_ms"] <= stats["completion_ms"]


def test_stream_ttft_counts_tool_call_delta():
    tool_chunk = {
        "id": "chatcmpl-t",
        "choices": [
            {"delta": {"tool_calls": [{"index": 0, "function": {"name": "sql"}}]}}
        ],
    }

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            content=_sse(tool_chunk, "[DONE]"),
            headers={"content-type": "text/event-stream"},
        )

    client = _client(handler)
    stats: dict = {}

    async def run():
        return [
            x
            async for x in client.stream_chat_completions(
                {"model": "m", "messages": [{"role": "user", "content": "x"}]}, stats
            )
        ]

    asyncio.run(run())
    assert stats["ttft_ms"] is not None


def test_stream_stats_are_per_call_not_shared():
    def handler(request: httpx.Request) -> httpx.Response:
        text = json.loads(request.content)["messages"][0]["content"]
        return httpx.Response(
            200,
            content=_sse(
                {"id": f"id-{text}", "choices": [{"delta": {"content": text}}]}, "[DONE]"
            ),
            headers={"content-type": "text/event-stream"},
        )

    client = _client(handler)  # ONE client instance shared by all concurrent calls

    async def one(tag: str) -> dict:
        stats: dict = {}
        async for _ in client.stream_chat_completions(
            {"model": "m", "messages": [{"role": "user", "content": tag}]}, stats
        ):
            await asyncio.sleep(0)
        return stats

    async def run():
        return await asyncio.gather(*(one(str(i)) for i in range(20)))

    all_stats = asyncio.run(run())
    assert [s["request_id"] for s in all_stats] == [f"id-{i}" for i in range(20)]


def test_stream_http_error_marks_stats_and_raises():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={"error": "boom"})

    client = _client(handler)
    stats: dict = {}

    async def run():
        async for _ in client.stream_chat_completions(
            {"model": "m", "messages": [{"role": "user", "content": "x"}]}, stats
        ):
            pass

    with pytest.raises(httpx.HTTPStatusError):
        asyncio.run(run())
    assert stats["status"] == "error"
