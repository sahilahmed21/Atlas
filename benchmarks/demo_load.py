#!/usr/bin/env python3
"""Drive live dashboard traffic that looks like real clients (not a metronome).

With prefix_aware + ATLAS_PREFIX_LOAD_MARGIN=1, a *single* shared system prefix
makes the gate alternate hit/gate forever (served pressure). This script's
default mix interleaves several tenant prefixes so the request log looks mixed.

Usage (from repo root, gateway already up)::

    $env:PYTHONPATH = "benchmarks"
    uv run python benchmarks/demo_load.py
    uv run python benchmarks/demo_load.py --mix realistic --n 48
"""

from __future__ import annotations

import argparse
import json
import random
import time
import urllib.error
import urllib.request

from traffic import MODEL, bursty, high_reuse, low_reuse, steady

BASE_DEFAULT = "http://127.0.0.1:8080"
KEY_DEFAULT = "sk-atlas-demo-key"

# Distinct system prompts = distinct prefix hashes (router keys on first system).
_TENANTS = (
    "You are Atlas legal. Cite policy briefly.",
    "You are Atlas support. Be concise and practical.",
    "You are Atlas analytics. Prefer numbers over prose.",
    "You are Atlas ops. Focus on runbooks and next steps.",
    "You are Atlas research. Summarize sources carefully.",
    "You are Atlas sales. Stay factual; no hype.",
)


def _body(system: str, user: str) -> dict:
    return {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "stream": False,
    }


def _post(base: str, key: str, body: dict, timeout: float = 60.0) -> tuple[str, str, str]:
    req = urllib.request.Request(
        base.rstrip("/") + "/v1/chat/completions",
        data=json.dumps(body).encode(),
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "User-Agent": "atlas-demo-load/1.0",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return (
            r.headers.get("x-atlas-worker-id") or "?",
            r.headers.get("x-atlas-cache-signal") or "?",
            (r.headers.get("x-atlas-route-reason") or "")[:96],
        )


def realistic(n: int, tenants: int = 5) -> list[dict]:
    """Interleaved multi-tenant sessions — not one prefix hammering the gate.

    Each step picks among: continue a warm tenant (short burst), start/switch
    tenant, or fire a one-shot cold prompt. Caps consecutive same-prefix rows
    so hit/gate cannot metronome the whole log under load_margin=1.
    """
    pool = list(_TENANTS[: max(2, min(tenants, len(_TENANTS)))])
    warm: list[str] = []  # recently used systems (affinity candidates)
    out: list[dict] = []
    turn = 0
    last_system: str | None = None
    run = 0

    def _emit(system: str, user: str) -> None:
        nonlocal turn, last_system, run
        turn += 1
        out.append(_body(system, user))
        if system == last_system:
            run += 1
        else:
            last_system = system
            run = 1
        if not system.startswith("Ephemeral task "):
            warm.append(system)
            if len(warm) > 12:
                del warm[:-8]

    while len(out) < n:
        # Force a switch if this tenant has run long enough.
        must_switch = last_system is not None and run >= 3
        roll = random.random()
        if warm and not must_switch and roll < 0.50:
            system = random.choice(warm[-min(3, len(warm)) :])
            _emit(system, f"follow-up {turn + 1}: what should I do next?")
        elif not must_switch and roll < 0.78:
            system = random.choice(pool)
            ask = random.choice(["status?", "explain briefly", "next step?"])
            _emit(system, f"session open {turn + 1}: {ask}")
        else:
            # Cold one-shot or forced switch away from a long run.
            if must_switch and pool:
                others = [s for s in pool if s != last_system] or pool
                system = random.choice(others)
                _emit(system, f"switch {turn + 1}: {random.choice(['status?', 'summarize'])}")
            else:
                system = f"Ephemeral task {turn + 1}-{random.randrange(1_000_000)}: one-shot helper."
                _emit(system, f"one-shot question {turn}")
    return out[:n]


def _build_bodies(n: int, mix: str, tenants: int) -> list[dict]:
    if mix == "realistic":
        return realistic(n, tenants=tenants)
    if mix == "sticky":
        # Explicit metronome — only use to show pure sticky / gate math.
        return high_reuse(n)
    if mix == "gated":
        # Gate-visible but interleaved: mostly warm tenants + some cold/steady.
        hot = realistic(max(1, int(n * 0.7)), tenants=max(3, tenants))
        cold = low_reuse(max(1, int(n * 0.15)))
        mid = steady(max(1, n - len(hot) - len(cold)))
        bodies = hot + cold + mid
        random.shuffle(bodies)
        return bodies[:n]
    if mix == "bursty":
        return bursty(n)
    raise ValueError(f"unknown mix: {mix}")


def _sleep_jitter(mean_ms: float, jitter_ms: float) -> None:
    delay = max(0.03, random.gauss(mean_ms / 1000.0, jitter_ms / 1000.0))
    time.sleep(delay)


def _prefix_diversity(bodies: list[dict]) -> int:
    systems = set()
    for b in bodies:
        for m in b.get("messages") or []:
            if m.get("role") == "system":
                systems.add(m.get("content") or "")
                break
    return len(systems)


def main() -> None:
    p = argparse.ArgumentParser(description="Atlas dashboard demo load (realistic pacing)")
    p.add_argument("--base", default=BASE_DEFAULT)
    p.add_argument("--key", default=KEY_DEFAULT)
    p.add_argument("--n", type=int, default=40)
    p.add_argument(
        "--mix",
        choices=("realistic", "gated", "sticky", "bursty"),
        default="realistic",
        help="realistic=interleaved tenants (default); sticky=single prefix (looks fake with gate on)",
    )
    p.add_argument("--tenants", type=int, default=5, help="tenant prefixes for realistic/gated")
    p.add_argument("--mean-ms", type=float, default=160.0, help="mean inter-request delay")
    p.add_argument("--jitter-ms", type=float, default=110.0, help="delay stddev")
    p.add_argument("--seed", type=int, default=None)
    args = p.parse_args()

    if args.seed is not None:
        random.seed(args.seed)

    bodies = _build_bodies(args.n, args.mix, args.tenants)
    print(
        f"demo_load mix={args.mix} n={len(bodies)} tenants≈{_prefix_diversity(bodies)} "
        f"mean_ms={args.mean_ms} → {args.base}"
    )
    if args.mix == "sticky":
        print(
            "note: sticky = one shared prefix; with load_margin=1 the log will "
            "alternate hit/gate — that is the gate, not a UI bug."
        )

    for i, body in enumerate(bodies):
        try:
            worker, signal, reason = _post(args.base, args.key, body)
            print(f"{i:02d}  {worker:10}  {signal:11}  {reason}")
        except urllib.error.HTTPError as e:
            print(f"{i:02d}  HTTP {e.code}: {e.read()[:120]!r}")
        except Exception as e:  # noqa: BLE001 — demo CLI
            print(f"{i:02d}  ERR {e}")
        if i + 1 < len(bodies):
            _sleep_jitter(args.mean_ms, args.jitter_ms)


if __name__ == "__main__":
    main()
