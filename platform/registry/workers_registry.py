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
    # Name of the env var holding the upstream API key; the secret itself is never stored here.
    api_key_env: str | None = None


def load_workers(path: str | Path) -> list[Worker]:
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    out: list[Worker] = []
    for row in raw.get("workers") or []:
        out.append(
            Worker(
                id=str(row["id"]),
                model=str(row["model"]),
                base_url=str(row["base_url"]).rstrip("/"),
                api_key_env=str(row["api_key_env"]) if row.get("api_key_env") else None,
            )
        )
    return out


def resolve_workers(workers: list[Worker], model: str) -> list[Worker]:
    return [w for w in workers if w.model == model]
