"""Phase 2 — token-id prefix cache simulation.

Hashes exact token-id prefixes (not raw text). Prefill accounting only.
Simplification: cache keys the whole shared prefix length (23), not vLLM
block-aligned APC pages — document that when reconciling in Phase 3.
"""

from __future__ import annotations

import csv
import hashlib
from pathlib import Path

SHARED_PREFIX_LEN = 23
SHARED_PREFIX = tuple(range(1000, 1000 + SHARED_PREFIX_LEN))

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUT = ROOT / "results" / "phase2" / "prefix_cache.csv"


def _key(tokens: tuple[int, ...]) -> str:
    raw = ",".join(str(t) for t in tokens).encode()
    return hashlib.sha256(raw).hexdigest()


def shared_prefix_traffic(n: int = 8) -> list[tuple[int, ...]]:
    """Phase 1–shaped: shared 23-token prefix + unique suffix (like [req=i])."""
    return [SHARED_PREFIX + (10_000 + i,) for i in range(n)]


def unique_prefix_traffic(n: int = 8) -> list[tuple[int, ...]]:
    return [tuple(range(i * 100, i * 100 + SHARED_PREFIX_LEN + 1)) for i in range(n)]


def run_cache(prompts: list[tuple[int, ...]], cacheable_len: int = SHARED_PREFIX_LEN) -> dict:
    cache: dict[str, int] = {}
    hits = 0
    misses = 0
    full_prefill = 0
    avoided = 0
    rows: list[dict] = []

    for i, prompt in enumerate(prompts):
        hit_len = 0
        # Longest cached prefix up to cacheable_len (teaching simplification)
        for L in range(min(len(prompt), cacheable_len), 0, -1):
            k = _key(prompt[:L])
            if k in cache:
                hit_len = L
                break

        if hit_len > 0:
            hits += 1
            prefill = len(prompt) - hit_len
            avoided += hit_len
            outcome = "hit"
        else:
            misses += 1
            prefill = len(prompt)
            outcome = "miss"
            # Insert cacheable prefix after a miss
            if len(prompt) >= cacheable_len:
                cache[_key(prompt[:cacheable_len])] = cacheable_len

        full_prefill += prefill
        rows.append(
            {
                "request_id": f"r{i}",
                "prompt_tokens": len(prompt),
                "hit_len": hit_len,
                "prefill_tokens": prefill,
                "outcome": outcome,
            }
        )

    return {
        "hits": hits,
        "misses": misses,
        "full_prefill_tokens": full_prefill,
        "avoided_prefill_tokens": avoided,
        "cacheable_prefix_len": cacheable_len,
        "rows": rows,
    }


def write_csv(path: Path, traffic_name: str, summary: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    write_header = not path.exists() or path.stat().st_size == 0
    fields = [
        "traffic",
        "request_id",
        "prompt_tokens",
        "hit_len",
        "prefill_tokens",
        "outcome",
        "hits_total",
        "misses_total",
        "full_prefill_tokens",
        "avoided_prefill_tokens",
        "cacheable_prefix_len",
    ]
    with path.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        if write_header:
            writer.writeheader()
        for row in summary["rows"]:
            writer.writerow(
                {
                    "traffic": traffic_name,
                    **row,
                    "hits_total": summary["hits"],
                    "misses_total": summary["misses"],
                    "full_prefill_tokens": summary["full_prefill_tokens"],
                    "avoided_prefill_tokens": summary["avoided_prefill_tokens"],
                    "cacheable_prefix_len": summary["cacheable_prefix_len"],
                }
            )


def main() -> int:
    out = DEFAULT_OUT
    if out.exists():
        out.unlink()
    shared = run_cache(shared_prefix_traffic())
    unique = run_cache(unique_prefix_traffic())
    write_csv(out, "shared_prefix", shared)
    write_csv(out, "unique_prefix", unique)
    print(
        f"shared hits={shared['hits']} misses={shared['misses']} "
        f"avoided={shared['avoided_prefill_tokens']}"
    )
    print(
        f"unique hits={unique['hits']} misses={unique['misses']} "
        f"avoided={unique['avoided_prefill_tokens']}"
    )
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
