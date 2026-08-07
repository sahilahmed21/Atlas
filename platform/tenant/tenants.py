"""YAML tenants + API-key auth (Phase 4 scaffolding)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass(frozen=True)
class Tenant:
    id: str
    api_key: str
    rpm_limit: int
    allowed_models: list[str]


def load_tenants(path: str | Path) -> list[Tenant]:
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    out: list[Tenant] = []
    for row in raw.get("tenants") or []:
        out.append(
            Tenant(
                id=str(row["id"]),
                api_key=str(row["api_key"]),
                rpm_limit=int(row.get("rpm_limit", 60)),
                allowed_models=[str(m) for m in (row.get("allowed_models") or [])],
            )
        )
    return out


def authenticate(tenants: list[Tenant], api_key: str | None) -> Tenant | None:
    if not api_key:
        return None
    for t in tenants:
        if t.api_key == api_key:
            return t
    return None
