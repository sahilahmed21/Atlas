"""Pure helpers for record/replay requests (no I/O): header parsing, hashing, usage parsing."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from typing import Any, Mapping

_RUN_ID = re.compile(r"^[A-Za-z0-9._:/-]{1,128}$")
MODES = {"live", "record", "replay"}


@dataclass(frozen=True)
class RecordCtx:
    mode: str  # "record" | "replay"
    run_id: str
    step: int
    req_body: bytes  # canonical JSON of the request, exactly what is hashed
    req_hash: str


def canonical_request(body: dict[str, Any]) -> bytes:
    return json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def parse_record_headers(
    headers: Mapping[str, str], body: dict[str, Any]
) -> tuple[RecordCtx | None, str | None]:
    """(None, None) = plain live request; (ctx, None) = record/replay; (None, msg) = invalid."""
    mode = (headers.get("x-atlas-mode") or "live").strip().lower()
    if mode not in MODES:
        return None, "x-atlas-mode must be one of: live, record, replay"
    if mode == "live":
        return None, None
    run_id = (headers.get("x-atlas-run-id") or "").strip()
    if not _RUN_ID.match(run_id):
        return None, "x-atlas-run-id is required (1-128 chars of A-Z a-z 0-9 . _ : / -)"
    raw_step = (headers.get("x-atlas-step") or "").strip()
    if not raw_step.isdigit():
        return None, "x-atlas-step is required and must be a non-negative integer"
    req_body = canonical_request(body)
    return (
        RecordCtx(mode, run_id, int(raw_step), req_body, hashlib.sha256(req_body).hexdigest()),
        None,
    )


# Synthetic faults only: every kind is deterministic and byte-identical on replay.
# (A latency spike depends on wall-clock time, so it is deliberately not a fault kind.)
FAULT_KINDS = ("rate_limit", "server_error", "timeout", "malformed_json", "truncated_stream")


@dataclass(frozen=True)
class FaultPlan:
    seed: int
    rate: float


def fault_for(seed: int, step: int, rate: float) -> str | None:
    """Pure function of (seed, step, rate): which fault, if any, hits this step."""
    u = int.from_bytes(hashlib.sha256(f"{seed}:{step}".encode()).digest()[:8], "big") / 2**64
    if u >= rate:
        return None
    return FAULT_KINDS[int(u / rate * len(FAULT_KINDS)) % len(FAULT_KINDS)]


def parse_fault_headers(headers: Mapping[str, str]) -> tuple[FaultPlan | None, str | None]:
    raw_seed = (headers.get("x-atlas-fault-seed") or "").strip()
    if not raw_seed:
        return None, None
    try:
        seed = int(raw_seed)
        rate = float((headers.get("x-atlas-fault-rate") or "0.25").strip())
    except ValueError:
        return None, "x-atlas-fault-seed must be an integer and x-atlas-fault-rate a number"
    if not 0.0 <= rate <= 1.0:
        return None, "x-atlas-fault-rate must be between 0 and 1"
    return FaultPlan(seed, rate), None


def _error_json(message: str, err_type: str) -> bytes:
    return json.dumps({"error": {"message": message, "type": err_type}}).encode("utf-8")


_TRUNCATED_JSON = (
    b'{"id":"chatcmpl-fault","object":"chat.completion","choices":[{"index":0,'
    b'"message":{"role":"assistant","content":"trunc'
)


def fault_payload(kind: str, stream: bool) -> tuple[int, bytes, bool]:
    """(status, body, body_is_sse) for an injected fault."""
    if kind == "rate_limit":
        return 429, _error_json("Rate limit exceeded (injected fault)", "rate_limit_error"), False
    if kind == "server_error":
        return 503, _error_json("Worker error: 503 (injected fault)", "upstream_error"), False
    if kind == "timeout":
        return 504, _error_json("Worker timed out (injected fault)", "upstream_timeout"), False
    if kind == "malformed_json":
        if stream:
            return 200, b"data: {not valid json\n\ndata: [DONE]\n\n", True
        return 200, _TRUNCATED_JSON, False
    if kind == "truncated_stream":
        if stream:
            chunk = (
                b'data: {"id":"chatcmpl-fault","object":"chat.completion.chunk",'
                b'"choices":[{"index":0,"delta":{"content":"partial"}}]}\n\n'
            )
            return 200, chunk, True  # no [DONE]: the stream just stops
        return 200, _TRUNCATED_JSON, False
    raise ValueError(f"unknown fault kind: {kind}")


def usage_from_json(body: dict[str, Any]) -> tuple[int | None, int | None]:
    usage = body.get("usage") if isinstance(body, dict) else None
    if not isinstance(usage, dict):
        return None, None
    return usage.get("prompt_tokens"), usage.get("completion_tokens")


def usage_from_sse(text: str) -> tuple[int | None, int | None]:
    """Last chunk carrying a usage object (present when the client sets stream_options)."""
    found: tuple[int | None, int | None] = (None, None)
    for line in text.splitlines():
        if not line.startswith("data:") or "[DONE]" in line:
            continue
        try:
            chunk = json.loads(line[5:].strip())
        except json.JSONDecodeError:
            continue
        got = usage_from_json(chunk)
        if got != (None, None):
            found = got
    return found


def sse_chunks(text: str) -> list[str]:
    """Split a recorded SSE body back into events; ''.join(result) == text."""
    parts = text.split("\n\n")
    out = [p + "\n\n" for p in parts[:-1]]
    if parts[-1]:
        out.append(parts[-1])
    return out
