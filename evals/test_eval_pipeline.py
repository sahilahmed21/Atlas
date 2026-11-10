"""RED/GREEN Phase 13: agent -> gateway (record/replay) -> runner -> report -> regression gate."""

import asyncio

import pytest

from harness import KEY, MODEL, Gateway


class Forbidden:
    async def chat_completions(self, payload, stats):
        raise AssertionError("replay must not reach the upstream")

    async def stream_chat_completions(self, payload, stats):
        raise AssertionError("replay must not reach the upstream")
        yield  # pragma: no cover


def _task(task_id):
    from tasks import TASKS

    return next(t for t in TASKS if t.id == task_id)


def _agent(gw, client, task, run_id, **kw):
    from agent import run_agent

    return run_agent(client, model=MODEL, question=task.question, tool=gw.tool, run_id=run_id,
                     api_key=KEY, **kw)


def test_agent_answers_through_tool_calls_and_the_run_is_recorded(tmp_path):
    from scripted_model import ScriptedModel
    from tasks import grade, ground_truth

    gw = Gateway(tmp_path, ScriptedModel(q=1.0))
    task = _task("total_orders")

    async def go():
        async with gw.client() as c:
            result = await _agent(gw, c, task, "run-1")
            return result, await gw.recorder.get_run("evals", "run-1")

    try:
        result, run = asyncio.run(go())
    finally:
        gw.close()

    assert result.status == "answered" and result.tool_calls == 1 and result.requests == 2
    assert grade(ground_truth(gw.db)["total_orders"], result.final_text)
    # the agent leaves the run lifecycle to the runner (which closes it; see the eval test below)
    assert [s["step"] for s in run["steps"]] == [0, 1] and run["status"] == "open"
    assert run["steps"][0]["prompt_tokens"] is not None


def test_agent_recovers_from_a_sql_error_and_tags_it(tmp_path):
    from scripted_model import ScriptedModel
    from tasks import grade, ground_truth

    gw = Gateway(tmp_path, ScriptedModel(q=1.0, typo_rate=1.0))

    async def go():
        async with gw.client() as c:
            return await _agent(gw, c, _task("total_orders"), "run-2")

    try:
        result = asyncio.run(go())
    finally:
        gw.close()

    assert result.status == "answered" and "tool_error" in result.tags and result.requests == 3
    assert grade(ground_truth(gw.db)["total_orders"], result.final_text)


def test_agent_stops_at_max_steps(tmp_path):
    from scripted_model import ScriptedModel

    gw = Gateway(tmp_path, ScriptedModel(q=1.0, never_answers=True))

    async def go():
        async with gw.client() as c:
            return await _agent(gw, c, _task("total_orders"), "run-3", max_steps=4)

    try:
        result = asyncio.run(go())
    finally:
        gw.close()

    assert result.status == "max_steps" and result.requests == 4 and result.final_text is None


def test_injected_http_faults_end_the_run_instead_of_looping(tmp_path):
    from scripted_model import ScriptedModel

    gw = Gateway(tmp_path, ScriptedModel(q=1.0))

    async def go():
        async with gw.client() as c:
            return await _agent(gw, c, _task("total_orders"), "run-4", fault_seed=1, fault_rate=1.0)

    try:
        result = asyncio.run(go())
    finally:
        gw.close()

    assert result.status == "http_error" and "http_error" in result.tags and result.requests <= 4


def _eval(gw, eval_id, k, tasks, concurrency=8, mode="record", run_prefix=None):
    from runner import run_eval
    from store import ResultStore

    store = ResultStore(gw.db.parent / f"{eval_id}.db")

    async def go():
        async with gw.client() as c:
            await run_eval(client=c, model=MODEL, api_key=KEY, tool=gw.tool, db_path=gw.db,
                           eval_id=eval_id, k=k, tasks=tasks, store=store,
                           concurrency=concurrency, mode=mode, run_prefix=run_prefix)

    asyncio.run(go())
    return store


def test_pass_hat_k_is_lower_than_pass_at_1_and_everything_is_recorded(tmp_path):
    from report import summarize
    from scripted_model import ScriptedModel
    from tasks import TASKS

    gw = Gateway(tmp_path, ScriptedModel(q=0.7, seed=11))
    tasks = TASKS[:12]
    try:
        store = _eval(gw, "e1", k=6, tasks=tasks)
        rows = store.rows("e1")
        closed = [asyncio.run(gw.recorder.get_run("evals", r["run_id"]))["status"] for r in rows]
    finally:
        gw.close()

    report = summarize(rows, k=6)
    assert len(rows) == 12 * 6 and set(closed) == {"closed"}
    assert report["pass_hat_k"]["mean"] < report["pass_at_1"]["mean"] < 1.0
    lo, hi = report["pass_at_1"]["ci95"]
    assert lo <= report["pass_at_1"]["mean"] <= hi
    assert report["flaky_tasks"] and all(0 < c < 6 for c in report["flaky_tasks"].values())
    assert report["failure_tags"].get("wrong_answer", 0) > 0


def test_cost_and_latency_are_attributed_per_step_from_the_run_log(tmp_path):
    from report import cost_latency
    from scripted_model import ScriptedModel
    from tasks import TASKS

    gw = Gateway(tmp_path, ScriptedModel(q=1.0))
    try:
        rows = _eval(gw, "e2", k=2, tasks=TASKS[:4]).rows("e2")
        stats = asyncio.run(cost_latency(gw.recorder, "evals", [r["run_id"] for r in rows],
                                         price_in_per_mtok=1.0, price_out_per_mtok=2.0))
    finally:
        gw.close()

    assert stats["steps"] == 4 * 2 * 2  # question step + answer step per trial
    assert stats["prompt_tokens"] > 0 and stats["completion_tokens"] > 0
    assert stats["cost_usd"] == pytest.approx(
        stats["prompt_tokens"] * 1.0 / 1e6 + stats["completion_tokens"] * 2.0 / 1e6)
    assert 0 < stats["latency_ms"]["p50"] <= stats["latency_ms"]["p95"]


def test_replay_reproduces_every_outcome_without_touching_the_model(tmp_path):
    from scripted_model import ScriptedModel
    from tasks import TASKS

    gw = Gateway(tmp_path, ScriptedModel(q=0.6, seed=5))
    tasks = TASKS[:8]
    try:
        recorded = _eval(gw, "rec", k=4, tasks=tasks).rows("rec")
        # same recorder, brand-new gateway whose model explodes if it is ever called
        replay_gw = Gateway(tmp_path / "replay", Forbidden(), recorder=gw.recorder)
        replayed = _eval(
            replay_gw, "rep", k=4, tasks=tasks, mode="replay", run_prefix="rec"
        ).rows("rep")
    finally:
        gw.close()

    key = lambda r: (r["task_id"], r["trial"])
    assert {key(r): (r["passed"], r["final_text"]) for r in recorded} == {
        key(r): (r["passed"], r["final_text"]) for r in replayed}


def test_gate_catches_a_seeded_regression_and_bisects_it_to_a_step(tmp_path):
    from gate import compare, first_divergence
    from scripted_model import ScriptedModel
    from tasks import TASKS

    tasks = TASKS[:16]
    base_gw = Gateway(tmp_path / "base", ScriptedModel(q=1.0, seed=1))
    cand_gw = Gateway(tmp_path / "cand", ScriptedModel(q=0.5, seed=1))
    try:
        base = _eval(base_gw, "base", k=4, tasks=tasks).rows("base")
        cand = _eval(cand_gw, "cand", k=4, tasks=tasks).rows("cand")
        same = compare(base, base, k=4)
        verdict = compare(base, cand, k=4)

        bad = next(r for r in cand if not r["passed"])
        good = next(r for r in base if (r["task_id"], r["trial"]) == (bad["task_id"], bad["trial"]))
        step = asyncio.run(first_divergence(
            base_gw.recorder, cand_gw.recorder, "evals", good["run_id"], bad["run_id"]))
    finally:
        base_gw.close(); cand_gw.close()

    assert same.passed and same.delta == 0.0
    assert not verdict.passed and verdict.delta < 0 and verdict.hi < 0
    assert step == 1  # step 0 (the question) is identical; the wrong tool result first shows at step 1
