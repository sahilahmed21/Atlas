"""RED/GREEN Phase 12: flight-recorder storage (idempotent steps, tenant namespace, restart-safe)."""

import asyncio
from pathlib import Path

import pytest


def _step(tenant="a", run="r1", step=0, req_hash="h0", resp=b'{"ok":1}', **kw):
    from recorder import Step

    base = dict(
        tenant_id=tenant,
        run_id=run,
        step=step,
        req_hash=req_hash,
        req_body=b'{"model":"m"}',
        resp_status=200,
        resp_body=resp,
        is_stream=False,
        worker_id="worker-a",
        ttft_ms=None,
        completion_ms=12.5,
        prompt_tokens=3,
        completion_tokens=4,
        fault=None,
        outcome="ok",
        ts=1000.0,
    )
    base.update(kw)
    return Step(**base)


def _run(coro):
    return asyncio.run(coro)


def test_commit_then_get_round_trips_bytes_exactly(tmp_path: Path):
    from recorder import Recorder

    async def go():
        rec = Recorder(tmp_path / "runs.db")
        try:
            raw = b'{"id":"x","choices":[{"message":{"content":"caf\xc3\xa9 \\u00e9"}}]}'
            await rec.commit_step(_step(resp=raw))
            got = await rec.get_step("a", "r1", 0)
            return raw, got
        finally:
            rec.close()

    raw, got = _run(go())
    assert got.resp_body == raw
    assert got.req_hash == "h0" and got.worker_id == "worker-a"
    assert got.completion_tokens == 4 and got.outcome == "ok"


def test_duplicate_commit_with_same_hash_returns_the_first_response(tmp_path: Path):
    from recorder import Recorder

    async def go():
        rec = Recorder(tmp_path / "runs.db")
        try:
            first = await rec.commit_step(_step(resp=b"FIRST"))
            second = await rec.commit_step(_step(resp=b"SECOND"))
            return first, second, await rec.get_step("a", "r1", 0)
        finally:
            rec.close()

    first, second, stored = _run(go())
    assert first.resp_body == second.resp_body == stored.resp_body == b"FIRST"


def test_same_step_different_hash_is_a_conflict_and_keeps_the_original(tmp_path: Path):
    from recorder import Recorder, StepConflict

    async def go():
        rec = Recorder(tmp_path / "runs.db")
        try:
            await rec.commit_step(_step(req_hash="h0", resp=b"ORIGINAL"))
            with pytest.raises(StepConflict):
                await rec.commit_step(_step(req_hash="OTHER", resp=b"INTRUDER"))
            return await rec.get_step("a", "r1", 0)
        finally:
            rec.close()

    assert _run(go()).resp_body == b"ORIGINAL"


def test_runs_are_namespaced_per_tenant(tmp_path: Path):
    from recorder import Recorder

    async def go():
        rec = Recorder(tmp_path / "runs.db")
        try:
            await rec.commit_step(_step(tenant="a", resp=b"A-DATA"))
            await rec.commit_step(_step(tenant="b", resp=b"B-DATA"))
            return (
                await rec.get_step("a", "r1", 0),
                await rec.get_step("b", "r1", 0),
                await rec.get_step("c", "r1", 0),
                await rec.get_run("c", "r1"),
            )
        finally:
            rec.close()

    a, b, c, run_c = _run(go())
    assert (a.resp_body, b.resp_body, c, run_c) == (b"A-DATA", b"B-DATA", None, None)


def test_steps_survive_a_process_restart(tmp_path: Path):
    from recorder import Recorder

    path = tmp_path / "runs.db"

    async def write():
        rec = Recorder(path)
        try:
            await rec.commit_step(_step(resp=b"DURABLE"))
        finally:
            rec.close()

    async def read():
        rec = Recorder(path)  # new process == new Recorder on the same file
        try:
            return await rec.get_step("a", "r1", 0)
        finally:
            rec.close()

    _run(write())
    assert _run(read()).resp_body == b"DURABLE"


def test_run_lifecycle_open_closed_incomplete(tmp_path: Path):
    from recorder import Recorder, RunClosed

    async def go():
        rec = Recorder(tmp_path / "runs.db")
        try:
            await rec.commit_step(_step(run="ok-run"))
            assert (await rec.get_run("a", "ok-run"))["status"] == "open"
            assert await rec.close_run("a", "ok-run") == "closed"
            with pytest.raises(RunClosed):
                await rec.commit_step(_step(run="ok-run", step=1, req_hash="h1"))

            await rec.commit_step(_step(run="bad-run"))
            rec.mark_incomplete("a", "bad-run")
            # closing an incomplete run must not launder it back to a clean state
            assert await rec.close_run("a", "bad-run") == "incomplete"
            assert await rec.close_run("a", "missing") is None
            return (await rec.get_run("a", "bad-run"))["status"]
        finally:
            rec.close()

    assert _run(go()) == "incomplete"


def test_get_run_lists_step_summaries_without_bodies(tmp_path: Path):
    from recorder import Recorder

    async def go():
        rec = Recorder(tmp_path / "runs.db")
        try:
            await rec.commit_step(_step(step=0, req_hash="h0", resp=b"SECRET-0"))
            await rec.commit_step(_step(step=1, req_hash="h1", resp=b"SECRET-1"))
            return await rec.get_run("a", "r1")
        finally:
            rec.close()

    run = _run(go())
    assert [s["step"] for s in run["steps"]] == [0, 1]
    assert [s["req_hash"] for s in run["steps"]] == ["h0", "h1"]
    assert "SECRET" not in repr(run)


def test_concurrent_commits_store_every_distinct_step(tmp_path: Path):
    from recorder import Recorder

    async def go():
        rec = Recorder(tmp_path / "runs.db")
        try:
            await asyncio.gather(
                *(rec.commit_step(_step(step=i, req_hash=f"h{i}", resp=f"R{i}".encode()))
                  for i in range(50))
            )
            return await rec.get_run("a", "r1")
        finally:
            rec.close()

    assert [s["step"] for s in _run(go())["steps"]] == list(range(50))


def test_concurrent_identical_commits_leave_exactly_one_row(tmp_path: Path):
    from recorder import Recorder

    async def go():
        rec = Recorder(tmp_path / "runs.db")
        try:
            results = await asyncio.gather(
                *(rec.commit_step(_step(resp=f"R{i}".encode())) for i in range(20))
            )
            return results, await rec.get_run("a", "r1")
        finally:
            rec.close()

    results, run = _run(go())
    assert len(run["steps"]) == 1
    assert len({r.resp_body for r in results}) == 1  # every caller sees the winner's response


def test_purge_before_deletes_old_runs_with_their_steps_and_keeps_newer(tmp_path: Path):
    import time

    from recorder import Recorder

    rec = Recorder(tmp_path / "r.db")
    try:
        _run(rec.commit_step(_step(run="old", ts=time.time())))
        time.sleep(0.05)
        cutoff = time.time()
        time.sleep(0.05)
        _run(rec.commit_step(_step(run="new", ts=time.time())))
        deleted = _run(rec.purge_before(cutoff))
        assert deleted == 1
        assert _run(rec.get_run("a", "old")) is None and _run(rec.get_step("a", "old", 0)) is None
        assert _run(rec.get_run("a", "new"))["steps"][0]["step"] == 0
    finally:
        rec.close()
