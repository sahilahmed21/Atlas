"""Phase 2 — static vs continuous batching simulation (CPU ticks).

Service units are simulated decode steps, not GPU tokens/s.
Do not compare busy fraction numerically to Phase 1 throughput.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from pathlib import Path

CAPACITY = 4
STATIC_BATCH = 4
STATIC_TIMEOUT = 5

# (request_id, arrival_tick, tokens_needed)
DEFAULT_TRACE: list[tuple[str, int, int]] = [
    ("r0", 0, 8),
    ("r1", 1, 8),
    ("r2", 2, 8),
    ("r3", 3, 8),
    ("r4", 20, 6),
    ("r5", 21, 6),
    ("r6", 40, 8),
    ("r7", 41, 4),
]

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUT = ROOT / "results" / "phase2" / "scheduler.csv"


@dataclass
class Req:
    rid: str
    arrival: int
    need: int
    remaining: int = field(init=False)
    start: int | None = None
    finish: int | None = None

    def __post_init__(self) -> None:
        self.remaining = self.need


def _load(trace: list[tuple[str, int, int]]) -> list[Req]:
    return [Req(rid, arrival, need) for rid, arrival, need in trace]


def run_static(
    trace: list[tuple[str, int, int]] = DEFAULT_TRACE,
    batch_size: int = STATIC_BATCH,
    timeout: int = STATIC_TIMEOUT,
    capacity: int = CAPACITY,
) -> dict:
    """Wait for batch full or timeout, then run that batch to completion before admitting more."""
    pending = sorted(_load(trace), key=lambda r: (r.arrival, r.rid))
    waiting: list[Req] = []
    t = 0
    busy = 0
    idle = 0
    completed = 0
    wait_started: int | None = None
    i = 0

    while completed < len(trace):
        while i < len(pending) and pending[i].arrival <= t:
            waiting.append(pending[i])
            if wait_started is None:
                wait_started = t
            i += 1

        ready = bool(waiting) and (
            len(waiting) >= batch_size
            or (wait_started is not None and t - wait_started >= timeout)
        )
        # If more work is still arriving later and we are not ready, idle forward
        if not ready:
            if i < len(pending):
                next_t = pending[i].arrival
                idle += max(next_t - t, 1)
                t = max(t + 1, next_t)
            elif waiting:
                # Force-fire remaining waiters (end of arrivals)
                ready = True
            else:
                break

        if not ready:
            continue

        batch = waiting[: min(batch_size, capacity, len(waiting))]
        waiting = waiting[len(batch) :]
        wait_started = t if waiting else None
        for r in batch:
            r.start = t

        while any(r.remaining > 0 for r in batch):
            for r in batch:
                if r.remaining > 0:
                    r.remaining -= 1
                    if r.remaining == 0:
                        r.finish = t + 1
                        completed += 1
            busy += 1
            t += 1

    latencies = [r.finish - r.arrival for r in _finished(pending)]
    total = busy + idle
    return {
        "design": "static",
        "completed": completed,
        "busy_ticks": busy,
        "idle_ticks": idle,
        "total_ticks": total,
        "busy_fraction": busy / total if total else 0.0,
        "mean_completion_latency": sum(latencies) / len(latencies) if latencies else 0.0,
        "work_completed": sum(r.need for r in pending),
        "params": {
            "capacity": capacity,
            "batch_size": batch_size,
            "timeout": timeout,
            "trace": "DEFAULT_TRACE",
        },
    }


def run_continuous(
    trace: list[tuple[str, int, int]] = DEFAULT_TRACE,
    capacity: int = CAPACITY,
) -> dict:
    pending = sorted(_load(trace), key=lambda r: (r.arrival, r.rid))
    queue: list[Req] = []
    active: list[Req] = []
    t = 0
    busy = 0
    idle = 0
    completed = 0
    i = 0

    while completed < len(trace):
        while i < len(pending) and pending[i].arrival <= t:
            queue.append(pending[i])
            i += 1

        active = [r for r in active if r.remaining > 0]
        while queue and len(active) < capacity:
            r = queue.pop(0)
            if r.start is None:
                r.start = t
            active.append(r)

        if active:
            for r in active:
                r.remaining -= 1
                if r.remaining == 0:
                    r.finish = t + 1
                    completed += 1
            busy += 1
            t += 1
        else:
            if i < len(pending):
                next_t = pending[i].arrival
                idle += max(next_t - t, 1)
                t = max(t + 1, next_t)
            else:
                break

    latencies = [r.finish - r.arrival for r in _finished(pending)]
    total = busy + idle
    return {
        "design": "continuous",
        "completed": completed,
        "busy_ticks": busy,
        "idle_ticks": idle,
        "total_ticks": total,
        "busy_fraction": busy / total if total else 0.0,
        "mean_completion_latency": sum(latencies) / len(latencies) if latencies else 0.0,
        "work_completed": sum(r.need for r in pending),
        "params": {
            "capacity": capacity,
            "batch_size": None,
            "timeout": None,
            "trace": "DEFAULT_TRACE",
        },
    }


def _finished(reqs: list[Req]) -> list[Req]:
    return [r for r in reqs if r.finish is not None]


def write_csv(path: Path, summaries: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "design",
        "completed",
        "busy_ticks",
        "idle_ticks",
        "total_ticks",
        "busy_fraction",
        "mean_completion_latency",
        "work_completed",
        "capacity",
        "batch_size",
        "timeout",
        "trace",
    ]
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for s in summaries:
            p = s["params"]
            writer.writerow(
                {
                    "design": s["design"],
                    "completed": s["completed"],
                    "busy_ticks": s["busy_ticks"],
                    "idle_ticks": s["idle_ticks"],
                    "total_ticks": s["total_ticks"],
                    "busy_fraction": f"{s['busy_fraction']:.4f}",
                    "mean_completion_latency": f"{s['mean_completion_latency']:.2f}",
                    "work_completed": s["work_completed"],
                    "capacity": p["capacity"],
                    "batch_size": p["batch_size"],
                    "timeout": p["timeout"],
                    "trace": p["trace"],
                }
            )


def main() -> int:
    static = run_static()
    continuous = run_continuous()
    write_csv(DEFAULT_OUT, [static, continuous])
    print(
        f"static     busy_fraction={static['busy_fraction']:.4f} "
        f"mean_lat={static['mean_completion_latency']:.2f}"
    )
    print(
        f"continuous busy_fraction={continuous['busy_fraction']:.4f} "
        f"mean_lat={continuous['mean_completion_latency']:.2f}"
    )
    print(f"wrote {DEFAULT_OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
