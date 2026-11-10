"""Eval results store (outcomes only; step content stays in the recorder, referenced by run_id)."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

_SCHEMA = """
CREATE TABLE IF NOT EXISTS results (
    eval_id    TEXT NOT NULL,
    task_id    TEXT NOT NULL,
    trial      INTEGER NOT NULL,
    run_id     TEXT NOT NULL,
    passed     INTEGER NOT NULL,
    status     TEXT NOT NULL,
    requests   INTEGER NOT NULL,
    tool_calls INTEGER NOT NULL,
    tags       TEXT NOT NULL,
    final_text TEXT,
    PRIMARY KEY (eval_id, task_id, trial)
) WITHOUT ROWID;
"""


class ResultStore:
    def __init__(self, path: str | Path) -> None:
        self._conn = sqlite3.connect(path)
        self._conn.executescript(_SCHEMA)

    def close(self) -> None:
        self._conn.close()

    def add(self, row: dict[str, Any]) -> None:
        with self._conn:
            self._conn.execute(
                "INSERT OR REPLACE INTO results VALUES (?,?,?,?,?,?,?,?,?,?)",
                (row["eval_id"], row["task_id"], row["trial"], row["run_id"], int(row["passed"]),
                 row["status"], row["requests"], row["tool_calls"], json.dumps(row["tags"]),
                 row["final_text"]),
            )

    def rows(self, eval_id: str) -> list[dict[str, Any]]:
        cur = self._conn.execute(
            "SELECT eval_id, task_id, trial, run_id, passed, status, requests, tool_calls, tags, "
            "final_text FROM results WHERE eval_id=? ORDER BY task_id, trial", (eval_id,))
        names = [d[0] for d in cur.description]
        out = []
        for values in cur.fetchall():
            row = dict(zip(names, values))
            row["passed"] = bool(row["passed"])
            row["tags"] = json.loads(row["tags"])
            out.append(row)
        return out
