"""Flight-recorder storage: one SQLite file, one writer thread that owns the connection.

Source of truth for recorded agent runs. A step is immutable once committed: committing the
same (tenant, run, step, request hash) again returns the stored step, a different hash is a
conflict. Every query is scoped by tenant_id.

# ponytail: single process + single file; move to Postgres only when writer latency or a
# second gateway replica demands it (measure first).
"""

from __future__ import annotations

import asyncio
import queue
import sqlite3
import threading
from dataclasses import astuple, dataclass, fields
from pathlib import Path
from typing import Any, Callable

SCHEMA_VERSION = 1

_SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
    tenant_id  TEXT NOT NULL,
    run_id     TEXT NOT NULL,
    created_at REAL NOT NULL,
    status     TEXT NOT NULL CHECK (status IN ('open', 'closed', 'incomplete')),
    PRIMARY KEY (tenant_id, run_id)
) WITHOUT ROWID;
CREATE INDEX IF NOT EXISTS runs_by_created ON runs (tenant_id, created_at);
CREATE TABLE IF NOT EXISTS steps (
    tenant_id         TEXT NOT NULL,
    run_id            TEXT NOT NULL,
    step              INTEGER NOT NULL CHECK (step >= 0),
    req_hash          TEXT NOT NULL,
    req_body          BLOB NOT NULL,
    resp_status       INTEGER NOT NULL,
    resp_body         BLOB NOT NULL,
    is_stream         INTEGER NOT NULL,
    worker_id         TEXT,
    ttft_ms           REAL,
    completion_ms     REAL,
    prompt_tokens     INTEGER,
    completion_tokens INTEGER,
    fault             TEXT,
    outcome           TEXT NOT NULL,
    ts                REAL NOT NULL,
    PRIMARY KEY (tenant_id, run_id, step),
    FOREIGN KEY (tenant_id, run_id) REFERENCES runs (tenant_id, run_id) ON DELETE CASCADE
) WITHOUT ROWID;
"""


class StepConflict(Exception):
    """Same (tenant, run, step) already recorded with a different request hash."""


class RunClosed(Exception):
    """New step for a run that was explicitly closed."""


class RecorderBusy(Exception):
    """Writer queue is full; the caller should shed load (503)."""


@dataclass(frozen=True)
class Step:
    tenant_id: str
    run_id: str
    step: int
    req_hash: str
    req_body: bytes
    resp_status: int
    resp_body: bytes
    is_stream: bool
    worker_id: str | None
    ttft_ms: float | None
    completion_ms: float | None
    prompt_tokens: int | None
    completion_tokens: int | None
    fault: str | None
    outcome: str
    ts: float


_COLS = [f.name for f in fields(Step)]
_SELECT = f"SELECT {', '.join(_COLS)} FROM steps"
_SUMMARY_COLS = [
    c for c in _COLS if c not in {"req_body", "resp_body", "tenant_id", "run_id"}
]


def _row_to_step(row: tuple) -> Step:
    values = list(row)
    values[_COLS.index("is_stream")] = bool(values[_COLS.index("is_stream")])
    return Step(*values)


class Recorder:
    def __init__(self, path: str | Path, max_queue: int = 1000) -> None:
        self._q: queue.Queue = queue.Queue(maxsize=max_queue)
        self._ready = threading.Event()
        self._init_error: BaseException | None = None
        self._thread = threading.Thread(
            target=self._writer, args=(str(path),), daemon=True, name="atlas-recorder"
        )
        self._thread.start()
        self._ready.wait()
        if self._init_error is not None:
            raise self._init_error

    # --- writer thread -------------------------------------------------------------------
    def _writer(self, path: str) -> None:
        try:
            conn = sqlite3.connect(path, isolation_level=None)  # explicit transactions below
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
            conn.execute("PRAGMA foreign_keys=ON")
            conn.execute("PRAGMA busy_timeout=5000")
            version = conn.execute("PRAGMA user_version").fetchone()[0]
            if version > SCHEMA_VERSION:
                raise RuntimeError(
                    f"recorder db schema v{version} is newer than this build (v{SCHEMA_VERSION})"
                )
            conn.executescript(_SCHEMA)
            conn.execute(f"PRAGMA user_version={SCHEMA_VERSION}")
        except BaseException as exc:  # surfaced to the constructor
            self._init_error = exc
            self._ready.set()
            return
        self._ready.set()
        try:
            while True:
                item = self._q.get()
                if item is None:
                    return
                fn, fut, loop, write = item
                try:
                    if write:
                        conn.execute("BEGIN IMMEDIATE")
                        try:
                            result = fn(conn)
                            conn.execute("COMMIT")
                        except BaseException:
                            conn.execute("ROLLBACK")
                            raise
                    else:  # reads need no write transaction (autocommit SELECT)
                        result = fn(conn)
                except Exception as exc:
                    self._resolve(fut, loop, error=exc)
                else:
                    self._resolve(fut, loop, result=result)
        finally:
            conn.close()

    @staticmethod
    def _resolve(fut, loop, result: Any = None, error: Exception | None = None) -> None:
        if fut is None:
            return

        def deliver() -> None:
            if fut.done():  # caller was cancelled
                return
            if error is not None:
                fut.set_exception(error)
            else:
                fut.set_result(result)

        try:
            loop.call_soon_threadsafe(deliver)
        except RuntimeError:  # loop already closed
            pass

    # --- plumbing -------------------------------------------------------------------------
    async def _submit(
        self, fn: Callable[[sqlite3.Connection], Any], write: bool = False
    ) -> Any:
        loop = asyncio.get_running_loop()
        fut = loop.create_future()
        try:
            self._q.put_nowait((fn, fut, loop, write))
        except queue.Full:
            raise RecorderBusy("recorder queue is full") from None
        return await fut

    def close(self) -> None:
        self._q.put(None)
        self._thread.join(timeout=10)

    # --- public API -----------------------------------------------------------------------
    async def get_step(self, tenant_id: str, run_id: str, step: int) -> Step | None:
        def fn(conn):
            row = conn.execute(
                f"{_SELECT} WHERE tenant_id=? AND run_id=? AND step=?",
                (tenant_id, run_id, step),
            ).fetchone()
            return _row_to_step(row) if row else None

        return await self._submit(fn)

    async def commit_step(self, step: Step) -> Step:
        """Idempotent insert. Returns the stored step (the first writer's, on a duplicate)."""

        def fn(conn):
            existing = conn.execute(
                f"{_SELECT} WHERE tenant_id=? AND run_id=? AND step=?",
                (step.tenant_id, step.run_id, step.step),
            ).fetchone()
            if existing:
                stored = _row_to_step(existing)
                if stored.req_hash != step.req_hash:
                    raise StepConflict(
                        f"step {step.step} of run {step.run_id} already recorded "
                        "with a different request"
                    )
                return stored
            run = conn.execute(
                "SELECT status FROM runs WHERE tenant_id=? AND run_id=?",
                (step.tenant_id, step.run_id),
            ).fetchone()
            if run and run[0] == "closed":
                raise RunClosed(f"run {step.run_id} is closed")
            conn.execute(
                "INSERT OR IGNORE INTO runs (tenant_id, run_id, created_at, status) "
                "VALUES (?, ?, ?, 'open')",
                (step.tenant_id, step.run_id, step.ts),
            )
            values = list(astuple(step))
            values[_COLS.index("is_stream")] = int(step.is_stream)
            conn.execute(
                f"INSERT INTO steps ({', '.join(_COLS)}) "
                f"VALUES ({', '.join('?' * len(_COLS))})",
                values,
            )
            return step

        return await self._submit(fn, write=True)

    def mark_incomplete(self, tenant_id: str, run_id: str) -> None:
        """Fire-and-forget (safe from a cancelled request): flag a run whose step was lost."""

        def fn(conn):
            conn.execute(
                "INSERT OR IGNORE INTO runs (tenant_id, run_id, created_at, status) "
                "VALUES (?, ?, strftime('%s','now'), 'incomplete')",
                (tenant_id, run_id),
            )
            conn.execute(
                "UPDATE runs SET status='incomplete' WHERE tenant_id=? AND run_id=?",
                (tenant_id, run_id),
            )

        try:
            self._q.put((fn, None, None, True), timeout=1.0)
        except queue.Full:
            raise RecorderBusy("recorder queue is full") from None

    async def close_run(self, tenant_id: str, run_id: str) -> str | None:
        """open -> closed. incomplete/closed stay as they are. None if the run is unknown."""

        def fn(conn):
            row = conn.execute(
                "SELECT status FROM runs WHERE tenant_id=? AND run_id=?", (tenant_id, run_id)
            ).fetchone()
            if row is None:
                return None
            if row[0] == "open":
                conn.execute(
                    "UPDATE runs SET status='closed' WHERE tenant_id=? AND run_id=?",
                    (tenant_id, run_id),
                )
                return "closed"
            return row[0]

        return await self._submit(fn, write=True)

    async def purge_before(self, cutoff_ts: float) -> int:
        """Retention: delete runs (and their steps, via cascade) created before cutoff_ts."""

        def fn(conn):
            return conn.execute("DELETE FROM runs WHERE created_at < ?", (cutoff_ts,)).rowcount

        return await self._submit(fn, write=True)

    async def get_run(self, tenant_id: str, run_id: str) -> dict[str, Any] | None:
        def fn(conn):
            run = conn.execute(
                "SELECT status, created_at FROM runs WHERE tenant_id=? AND run_id=?",
                (tenant_id, run_id),
            ).fetchone()
            if run is None:
                return None
            rows = conn.execute(
                f"SELECT {', '.join(_SUMMARY_COLS)} FROM steps "
                "WHERE tenant_id=? AND run_id=? ORDER BY step",
                (tenant_id, run_id),
            ).fetchall()
            return {
                "run_id": run_id,
                "status": run[0],
                "created_at": run[1],
                "steps": [
                    {**dict(zip(_SUMMARY_COLS, r)), "is_stream": bool(r[_SUMMARY_COLS.index("is_stream")])}
                    for r in rows
                ],
            }

        return await self._submit(fn)
