"""One-command offline demo: record agent runs, replay them identically, catch a regression.

    python evals/demo.py

Uses the scripted offline model (evals/scripted_model.py), so it needs no API key and says
nothing about any real LLM: it demonstrates the recording / replay / reliability machinery.
"""

from __future__ import annotations

import asyncio
import json
import sys
import tempfile
from pathlib import Path

from gate import compare, first_divergence
from harness import KEY, MODEL, TENANT, Gateway
from report import summarize
from runner import run_eval
from scripted_model import ScriptedModel
from store import ResultStore
from tasks import TASKS

K = 6
TASK_COUNT = 16


class _NoModel:
    """Replay must never reach a model; if it does, fail loudly."""

    calls = 0

    async def chat_completions(self, payload, stats):
        _NoModel.calls += 1
        raise AssertionError("replay reached the model")

    async def stream_chat_completions(self, payload, stats):
        _NoModel.calls += 1
        raise AssertionError("replay reached the model")
        yield  # pragma: no cover


def _run(gw: Gateway, eval_id: str, mode: str = "record", run_prefix: str | None = None) -> list[dict]:
    store = ResultStore(gw.db.parent / f"{eval_id}.db")

    async def go():
        async with gw.client() as client:
            await run_eval(client=client, model=MODEL, api_key=KEY, tool=gw.tool, db_path=gw.db,
                           eval_id=eval_id, k=K, tasks=TASKS[:TASK_COUNT], store=store,
                           mode=mode, run_prefix=run_prefix)

    asyncio.run(go())
    try:
        return store.rows(eval_id)
    finally:
        store.close()


def main(workdir: Path) -> dict:
    tasks = TASKS[:TASK_COUNT]
    base = Gateway(workdir / "baseline", ScriptedModel(q=0.8, seed=3))
    worse = Gateway(workdir / "candidate", ScriptedModel(q=0.5, seed=3))
    try:
        recorded = _run(base, "baseline")
        report = summarize(recorded, K)

        replay_gw = Gateway(workdir / "replay", _NoModel(), recorder=base.recorder)
        replayed = _run(replay_gw, "replay", mode="replay", run_prefix="baseline")
        outcome = lambda rows: {(r["task_id"], r["trial"]): (r["passed"], r["final_text"]) for r in rows}
        replay_identical = outcome(recorded) == outcome(replayed) and _NoModel.calls == 0

        candidate = _run(worse, "candidate")
        verdict = compare(recorded, candidate, K)
        bad = next((r for r in candidate if not r["passed"]), None)
        step = None
        if bad is not None:
            good = next(r for r in recorded if (r["task_id"], r["trial"]) == (bad["task_id"], bad["trial"]))
            step = asyncio.run(first_divergence(base.recorder, worse.recorder, TENANT,
                                                good["run_id"], bad["run_id"]))
    finally:
        base.close()
        worse.close()

    return {
        "trials": len(recorded), "tasks": len(tasks), "k": K, "report": report,
        "replay_identical": replay_identical, "model_calls_during_replay": _NoModel.calls,
        "gate_failed": not verdict.passed, "gate_delta": verdict.delta,
        "gate_ci95": [verdict.lo, verdict.hi], "diverges_at_step": step,
    }


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1]
    for sub in ("platform/gateway", "platform/tenant", "platform/registry", "platform/router",
                "platform/observability", "platform/recorder", "workers", "evals"):
        sys.path.insert(0, str(root / sub))
    with tempfile.TemporaryDirectory() as tmp:
        print(json.dumps(main(Path(tmp)), indent=2, default=list))
