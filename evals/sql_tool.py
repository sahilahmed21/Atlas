"""Read-only SQL tool for the eval agent: one statement, row-capped, time-capped."""

from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path

_ALLOWED = {sqlite3.SQLITE_SELECT, sqlite3.SQLITE_READ, sqlite3.SQLITE_FUNCTION, sqlite3.SQLITE_RECURSIVE}


def _authorizer(action, *_):
    return sqlite3.SQLITE_OK if action in _ALLOWED else sqlite3.SQLITE_DENY


class SqlTool:
    """Defence in depth: read-only connection + query_only + authorizer (no ATTACH/PRAGMA/DDL)."""

    def __init__(self, db_path: str | Path, max_rows: int = 50, timeout_s: float = 5.0) -> None:
        self._uri = Path(db_path).resolve().as_uri() + "?mode=ro"
        self.max_rows = max_rows
        self.timeout_s = timeout_s

    def run(self, sql: str) -> str:
        conn = sqlite3.connect(self._uri, uri=True)
        try:
            conn.execute("PRAGMA query_only=ON")
            conn.set_authorizer(_authorizer)
            deadline = time.monotonic() + self.timeout_s
            conn.set_progress_handler(lambda: 1 if time.monotonic() > deadline else 0, 10_000)
            cur = conn.execute(sql)
            columns = [d[0] for d in cur.description] if cur.description else []
            rows = cur.fetchmany(self.max_rows + 1)
            return json.dumps(
                {"columns": columns, "rows": [list(r) for r in rows[: self.max_rows]],
                 "truncated": len(rows) > self.max_rows}
            )
        except sqlite3.Error as exc:
            return json.dumps({"error": str(exc)})
        finally:
            conn.close()
