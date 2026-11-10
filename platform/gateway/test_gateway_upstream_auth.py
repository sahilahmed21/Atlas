"""RED/GREEN Phase 11b: workers with api_key_env resolve their key at startup or fail fast."""

from pathlib import Path

import pytest

MODEL = "m"


def _files(tmp_path: Path):
    t = tmp_path / "t.yaml"
    t.write_text(
        "tenants:\n  - id: demo\n    api_key: sk-atlas-demo-key\n    rpm_limit: 10\n"
        f"    allowed_models: [{MODEL}]\n",
        encoding="utf-8",
    )
    w = tmp_path / "w.yaml"
    w.write_text(
        f"workers:\n  - id: hosted\n    model: {MODEL}\n    base_url: https://api.example/v1\n"
        "    api_key_env: ATLAS_TEST_UPSTREAM_KEY\n",
        encoding="utf-8",
    )
    return t, w


def test_missing_upstream_key_env_fails_startup_naming_the_variable(tmp_path: Path, monkeypatch):
    from app import create_app

    monkeypatch.delenv("ATLAS_TEST_UPSTREAM_KEY", raising=False)
    t, w = _files(tmp_path)

    with pytest.raises(RuntimeError, match="ATLAS_TEST_UPSTREAM_KEY"):
        create_app(tenants_path=t, workers_path=w)


def test_upstream_key_present_starts_and_is_not_leaked_in_the_app_state(tmp_path: Path, monkeypatch):
    from app import create_app

    monkeypatch.setenv("ATLAS_TEST_UPSTREAM_KEY", "sk-super-secret")
    t, w = _files(tmp_path)

    app = create_app(tenants_path=t, workers_path=w)

    assert "sk-super-secret" not in repr(app.state.workers)
