"""YAML worker registry (Phase 4 scaffolding)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass(frozen=True)
class Worker:
    id: str
    model: str
    base_url: str


def load_workers(path: str | Path) -> list[Worker]:
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    out: list[Worker] = []
    for row in raw.get("workers") or []:
        out.append(
            Worker(
                id=str(row["id"]),
                model=str(row["model"]),
                base_url=str(row["base_url"]).rstrip("/"),
            )
        )
    return out


def resolve_workers(workers: list[Worker], model: str) -> list[Worker]:
    return [w for w in workers if w.model == model]
