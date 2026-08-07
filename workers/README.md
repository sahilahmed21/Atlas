# workers/

Model servers only (vLLM OpenAI-compatible). No API keys, no billing, no routing policy.

| Path | Role |
| --- | --- |
| `openai_worker_client.py` | Thin `POST /chat/completions` client |
| `test_openai_worker_client.py` | httpx MockTransport contract tests |
