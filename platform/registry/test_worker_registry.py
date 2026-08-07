"""RED/GREEN: YAML worker registry resolve-by-model (AC-004)."""

from pathlib import Path


def _write_workers(path: Path) -> Path:
    path.write_text(
        "workers:\n"
        "  - id: worker-a\n"
        "    model: Qwen/Qwen2.5-0.5B-Instruct\n"
        "    base_url: http://127.0.0.1:8001/v1\n"
        "  - id: worker-b\n"
        "    model: Qwen/Qwen2.5-0.5B-Instruct\n"
        "    base_url: http://127.0.0.1:8002/v1\n"
        "  - id: worker-c\n"
        "    model: other/model\n"
        "    base_url: http://127.0.0.1:8003/v1\n",
        encoding="utf-8",
    )
    return path


def test_load_workers_from_yaml(tmp_path: Path):
    from workers_registry import load_workers

    workers = load_workers(_write_workers(tmp_path / "workers.yaml"))
    assert [w.id for w in workers] == ["worker-a", "worker-b", "worker-c"]
    assert workers[0].base_url.endswith("/v1")


def test_resolve_workers_by_model(tmp_path: Path):
    from workers_registry import load_workers, resolve_workers

    workers = load_workers(_write_workers(tmp_path / "workers.yaml"))
    matched = resolve_workers(workers, "Qwen/Qwen2.5-0.5B-Instruct")

    assert [w.id for w in matched] == ["worker-a", "worker-b"]


def test_resolve_unknown_model_returns_empty(tmp_path: Path):
    from workers_registry import load_workers, resolve_workers

    workers = load_workers(_write_workers(tmp_path / "workers.yaml"))
    assert resolve_workers(workers, "missing/model") == []
