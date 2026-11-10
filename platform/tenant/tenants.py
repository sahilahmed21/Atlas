"""YAML tenants + API-key auth (Phase 4 scaffolding)."""

from __future__ import annotations

import hmac
from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass(frozen=True)
class Tenant:
    id: str
    api_key: str
    rpm_limit: int
    allowed_models: list[str]
    # Stored runs contain prompt/response text, so recording and replay are opt-in per tenant.
    record_allowed: bool = False


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
                record_allowed=row.get("record_allowed", False) is True,
            )
        )
    return out


def authenticate(tenants: list[Tenant], api_key: str | None) -> Tenant | None:
    if not api_key:
        return None
    presented = api_key.encode("utf-8")
    match: Tenant | None = None
    # Compare against every tenant (no early exit) with a constant-time compare.
    for t in tenants:
        if hmac.compare_digest(t.api_key.encode("utf-8"), presented):
            match = t
    return match
