"""Phase 2 — contiguous vs paged KV allocator simulation (CPU only).

Teaching model of reservation waste under variable sequence lengths.
Not a CUDA kernel and not an explanation of Phase 1 GPU peak VRAM.
"""

from __future__ import annotations

import csv
import math
from pathlib import Path

# Phase 1 Qwen2.5-0.5B: KV_bytes = B * S * 12288
BYTES_PER_TOKEN = 12288
BLOCK_SIZE = 16

# (request_id, max_len, used_len) — variable S; max_len >> used for over-reserve cases
DEFAULT_TRACE: list[tuple[str, int, int]] = [
    ("r0", 512, 40),
    ("r1", 512, 200),
    ("r2", 2048, 100),
    ("r3", 2048, 1800),
    ("r4", 128, 128),
    ("r5", 1024, 16),
]

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUT = ROOT / "results" / "phase2" / "allocator.csv"

CSV_FIELDS = [
    "design",
    "request_id",
    "max_tokens",
    "used_tokens",
    "reserved_tokens",
    "reserved_bytes",
    "used_bytes",
    "waste_bytes",
    "outcome",
    "notes",
]


def run_contiguous(
    trace: list[tuple[str, int, int]] = DEFAULT_TRACE,
    bytes_per_token: int = BYTES_PER_TOKEN,
) -> list[dict]:
    rows: list[dict] = []
    for rid, max_len, used in trace:
        if used > max_len:
            raise ValueError(f"{rid}: used {used} > max_len {max_len}")
        reserved = max_len
        rows.append(
            {
                "design": "contiguous",
                "request_id": rid,
                "max_tokens": max_len,
                "used_tokens": used,
                "reserved_tokens": reserved,
                "reserved_bytes": reserved * bytes_per_token,
                "used_bytes": used * bytes_per_token,
                "waste_bytes": (reserved - used) * bytes_per_token,
                "outcome": "ok",
                "notes": "reserve_max_len",
            }
        )
    return rows


def run_paged(
    trace: list[tuple[str, int, int]] = DEFAULT_TRACE,
    bytes_per_token: int = BYTES_PER_TOKEN,
    block_size: int = BLOCK_SIZE,
) -> list[dict]:
    rows: list[dict] = []
    for rid, max_len, used in trace:
        if used > max_len:
            raise ValueError(f"{rid}: used {used} > max_len {max_len}")
        n_blocks = math.ceil(used / block_size) if used else 0
        reserved = n_blocks * block_size
        rows.append(
            {
                "design": "paged",
                "request_id": rid,
                "max_tokens": max_len,
                "used_tokens": used,
                "reserved_tokens": reserved,
                "reserved_bytes": reserved * bytes_per_token,
                "used_bytes": used * bytes_per_token,
                "waste_bytes": (reserved - used) * bytes_per_token,
                "outcome": "ok",
                "notes": f"block_size={block_size}; blocks={n_blocks}",
            }
        )
    return rows


def summarize(rows: list[dict]) -> dict:
    return {
        "total_reserved_bytes": sum(r["reserved_bytes"] for r in rows),
        "total_used_bytes": sum(r["used_bytes"] for r in rows),
        "total_waste_bytes": sum(r["waste_bytes"] for r in rows),
        "n_requests": len(rows),
    }


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k) for k in CSV_FIELDS})


def main() -> int:
    contig = run_contiguous()
    paged = run_paged()
    write_csv(DEFAULT_OUT, contig + paged)
    sc, sp = summarize(contig), summarize(paged)
    print(f"contiguous waste_bytes={sc['total_waste_bytes']}")
    print(f"paged      waste_bytes={sp['total_waste_bytes']}")
    print(f"wrote {DEFAULT_OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
