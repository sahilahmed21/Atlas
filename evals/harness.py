"""In-process gateway + recorder + task database, shared by the tests and the offline demo."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import httpx

MODEL = "scripted-model"
KEY = "sk-eval"
TENANT = "evals"


class Gateway:
    def __init__(self, workdir: Path, upstream: Any, recorder: Any = None) -> None:
        from app import create_app
        from dataset import DEFAULT_SEED, build_db
        from recorder import Recorder
        from sql_tool import SqlTool

        workdir.mkdir(parents=True, exist_ok=True)
        (workdir / "t.yaml").write_text(
            f"tenants:\n  - id: {TENANT}\n    api_key: {KEY}\n    rpm_limit: 1000000\n"
            f"    record_allowed: true\n    allowed_models: [{MODEL}]\n", encoding="utf-8")
        (workdir / "w.yaml").write_text(
            f"workers:\n  - id: w\n    model: {MODEL}\n    base_url: http://scripted/v1\n",
            encoding="utf-8")
        self.db = build_db(workdir / "data.db", DEFAULT_SEED)
        self.tool = SqlTool(self.db)
        self.recorder = recorder or Recorder(workdir / "runs.db")
        self.app = create_app(
            tenants_path=workdir / "t.yaml", workers_path=workdir / "w.yaml",
            worker_client_factory=lambda _u: upstream, recorder=self.recorder)

    def client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(transport=httpx.ASGITransport(app=self.app), base_url="http://gw")

    def close(self) -> None:
        self.recorder.close()
