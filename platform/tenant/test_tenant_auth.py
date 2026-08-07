"""RED/GREEN: YAML tenant load + API-key auth (AC-003)."""

from pathlib import Path

import pytest


def _write_tenants(path: Path) -> Path:
    path.write_text(
        "tenants:\n"
        "  - id: demo\n"
        "    api_key: sk-atlas-demo-key\n"
        "    rpm_limit: 60\n"
        "    allowed_models:\n"
        "      - Qwen/Qwen2.5-0.5B-Instruct\n"
        "  - id: other\n"
        "    api_key: sk-atlas-other-key\n"
        "    rpm_limit: 30\n"
        "    allowed_models:\n"
        "      - Qwen/Qwen2.5-0.5B-Instruct\n",
        encoding="utf-8",
    )
    return path


def test_load_tenants_from_yaml(tmp_path: Path):
    from tenants import load_tenants

    cfg = _write_tenants(tmp_path / "tenants.yaml")
    tenants = load_tenants(cfg)

    assert len(tenants) == 2
    assert tenants[0].id == "demo"
    assert tenants[0].api_key == "sk-atlas-demo-key"
    assert tenants[0].allowed_models == ["Qwen/Qwen2.5-0.5B-Instruct"]


def test_authenticate_returns_tenant_for_valid_key(tmp_path: Path):
    from tenants import authenticate, load_tenants

    tenants = load_tenants(_write_tenants(tmp_path / "tenants.yaml"))
    tenant = authenticate(tenants, "sk-atlas-other-key")

    assert tenant is not None
    assert tenant.id == "other"


def test_authenticate_returns_none_for_unknown_key(tmp_path: Path):
    from tenants import authenticate, load_tenants

    tenants = load_tenants(_write_tenants(tmp_path / "tenants.yaml"))
    assert authenticate(tenants, "sk-nope") is None


def test_authenticate_rejects_empty_key(tmp_path: Path):
    from tenants import authenticate, load_tenants

    tenants = load_tenants(_write_tenants(tmp_path / "tenants.yaml"))
    assert authenticate(tenants, "") is None
    assert authenticate(tenants, None) is None  # type: ignore[arg-type]
