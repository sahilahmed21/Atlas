"""RED/GREEN Phase 13: synthetic dataset, SQL task suite with computed ground truth, SQL tool."""

import hashlib
import sqlite3
from pathlib import Path

import pytest


def _digest(path: Path) -> str:
    conn = sqlite3.connect(path)
    try:
        rows = conn.execute("SELECT * FROM orders ORDER BY id").fetchall()
        rows += conn.execute("SELECT * FROM customers ORDER BY id").fetchall()
        return hashlib.sha256(repr(rows).encode()).hexdigest()
    finally:
        conn.close()


def test_dataset_is_deterministic_per_seed(tmp_path: Path):
    from dataset import build_db

    build_db(tmp_path / "a.db", seed=1)
    build_db(tmp_path / "b.db", seed=1)
    build_db(tmp_path / "c.db", seed=2)

    assert _digest(tmp_path / "a.db") == _digest(tmp_path / "b.db") != _digest(tmp_path / "c.db")


def test_suite_has_at_least_30_unique_tasks_with_single_value_ground_truth(tmp_path: Path):
    from dataset import build_db
    from tasks import TASKS, ground_truth

    build_db(tmp_path / "d.db", seed=1)
    truth = ground_truth(tmp_path / "d.db")

    assert len(TASKS) >= 30 and len({t.id for t in TASKS}) == len(TASKS)
    assert set(truth) == {t.id for t in TASKS}
    assert all(v not in (None, "") for v in truth.values())


def test_argmax_tasks_have_no_ties_on_the_default_dataset(tmp_path: Path):
    from dataset import DEFAULT_SEED, build_db
    from tasks import tie_margins

    build_db(tmp_path / "d.db", seed=DEFAULT_SEED)

    assert all(margin > 0 for margin in tie_margins(tmp_path / "d.db").values())


@pytest.mark.parametrize(
    "expected,answer,ok",
    [
        (1234.5, "ANSWER: 1234.5", True),
        (1234.5, "The total is ANSWER: 1,234.50", True),
        (1234.5, "ANSWER: $1234.5", True),
        (1234.5, "ANSWER: 1234.51", False),
        (42, "ANSWER: 42", True),
        (42, "ANSWER: 42.0", True),
        (42, "ANSWER: 43", False),
        ("north", "ANSWER: North", True),
        ("north", "ANSWER: south", False),
        (42, "I think it is 42", False),  # no ANSWER: line -> not gradable -> fail
        (42, "", False),
        (42, None, False),
    ],
)
def test_grader(expected, answer, ok):
    from tasks import grade

    assert grade(expected, answer) is ok


def test_sql_tool_runs_select_and_caps_rows(tmp_path: Path):
    import json

    from dataset import build_db
    from sql_tool import SqlTool

    build_db(tmp_path / "d.db", seed=1)
    tool = SqlTool(tmp_path / "d.db", max_rows=5)

    ok = json.loads(tool.run("SELECT id, region FROM customers ORDER BY id"))
    assert ok["columns"] == ["id", "region"] and len(ok["rows"]) == 5 and ok["truncated"] is True
    assert "error" in json.loads(tool.run("SELEC nope"))


@pytest.mark.parametrize(
    "sql",
    [
        "INSERT INTO customers VALUES (9999,'x','y')",
        "DROP TABLE orders",
        "UPDATE orders SET amount = 0",
        "ATTACH DATABASE ':memory:' AS evil",
    ],
)
def test_sql_tool_cannot_modify_the_database(tmp_path: Path, sql):
    import json

    from dataset import build_db
    from sql_tool import SqlTool

    db = tmp_path / "d.db"
    build_db(db, seed=1)
    before = _digest(db)

    assert "error" in json.loads(SqlTool(db).run(sql))
    assert _digest(db) == before


def test_sql_tool_aborts_runaway_queries(tmp_path: Path):
    import json
    import time

    from dataset import build_db
    from sql_tool import SqlTool

    build_db(tmp_path / "d.db", seed=1)
    tool = SqlTool(tmp_path / "d.db", timeout_s=0.5)
    forever = "WITH RECURSIVE r(n) AS (SELECT 1 UNION ALL SELECT n+1 FROM r) SELECT count(*) FROM r"

    t0 = time.perf_counter()
    result = json.loads(tool.run(forever))

    assert "error" in result and time.perf_counter() - t0 < 5
