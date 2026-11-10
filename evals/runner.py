"""Eval runner: k trials per task, bounded concurrency, one gateway run per trial."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

import httpx

from agent import run_agent
from sql_tool import SqlTool
from store import ResultStore
from tasks import Task, grade, ground_truth


async def run_eval(
    *,
    client: httpx.AsyncClient,
    model: str,
    api_key: str,
    tool: SqlTool,
    db_path: str | Path,
    eval_id: str,
    k: int,
    tasks: list[Task],
    store: ResultStore,
    concurrency: int = 8,
    mode: str = "record",
    run_prefix: str | None = None,
    max_steps: int = 8,
    fault_seed: int | None = None,
    fault_rate: float | None = None,
) -> None:
    """mode='replay' re-runs recorded trials (run_prefix = the recorded eval_id) without the model."""
    truth = ground_truth(db_path)
    prefix = run_prefix or eval_id
    gate = asyncio.Semaphore(concurrency)
    auth = {"Authorization": f"Bearer {api_key}"}

    async def one(task: Task, trial: int) -> None:
        run_id = f"{prefix}/{task.id}/{trial}"
        async with gate:
            result = await run_agent(
                client, model=model, question=task.question, tool=tool, run_id=run_id,
                api_key=api_key, max_steps=max_steps, mode=mode, user_tag=f"{task.id}#{trial}",
                fault_seed=fault_seed, fault_rate=fault_rate,
            )
            passed = result.status == "answered" and grade(truth[task.id], result.final_text)
            tags = list(result.tags)
            if not passed:
                tags.append("wrong_answer" if result.status == "answered" else "no_answer")
            row: dict[str, Any] = {
                "eval_id": eval_id, "task_id": task.id, "trial": trial, "run_id": run_id,
                "passed": passed, "status": result.status, "requests": result.requests,
                "tool_calls": result.tool_calls, "tags": tags, "final_text": result.final_text,
            }
            store.add(row)
            if mode == "record":
                await client.post(f"/atlas/runs/{run_id}/end", headers=auth)

    await asyncio.gather(*(one(t, i) for t in tasks for i in range(k)))
