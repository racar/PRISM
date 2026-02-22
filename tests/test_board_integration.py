from __future__ import annotations

import asyncio
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from prism.board.flux_client import FluxClient
from prism.board.task_mapper import ParsedEpic, ParsedTask, _parse_epics
from prism.board.webhook_listener import app, set_project_dir
from prism.cli.sync import (
    _load_mapping,
    _normalize_mapping,
    _save_mapping,
    _sync_epics,
    _task_content_hash,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

_TASK_COUNTER = 0


def _make_flux_response(title: str, status: str = "todo") -> dict:
    global _TASK_COUNTER
    _TASK_COUNTER += 1
    return {
        "id": f"t-{_TASK_COUNTER}",
        "title": title,
        "status": status,
        "description": "",
    }


def _make_epic_response(title: str) -> dict:
    global _TASK_COUNTER
    _TASK_COUNTER += 1
    return {"id": f"e-{_TASK_COUNTER}", "title": title, "description": ""}


def _make_project_response(name: str) -> dict:
    return {"id": "proj-auto-1", "name": name}


@pytest.fixture(autouse=True)
def _reset_counter():
    global _TASK_COUNTER
    _TASK_COUNTER = 0


@pytest.fixture
def proj_dir(tmp_path) -> Path:
    prism_dir = tmp_path / ".prism"
    prism_dir.mkdir()
    return tmp_path


@pytest.fixture
def sample_epics() -> list[ParsedEpic]:
    return [
        ParsedEpic(
            "Auth",
            "Authentication epic",
            [
                ParsedTask("Login", "Build login", ["Returns 200", "Returns 401"]),
                ParsedTask("Register", "Build register", ["Validates email"]),
            ],
        ),
    ]


@pytest.fixture
def webhook_client():
    return TestClient(app)


class StatefulFluxMock:
    def __init__(self):
        self.tasks: dict[str, dict] = {}
        self.epics: dict[str, dict] = {}
        self.calls: list[tuple[str, str]] = []

    def handle(self, method: str, url: str, **kwargs) -> MagicMock:
        self.calls.append((method, url))
        resp = MagicMock()
        resp.raise_for_status = MagicMock()

        if method == "POST" and "/epics" in url:
            title = kwargs.get("json", {}).get("title", "Epic")
            data = _make_epic_response(title)
            self.epics[data["id"]] = data
            resp.json.return_value = data
        elif method == "POST" and "/tasks" in url:
            payload = kwargs.get("json", {})
            data = _make_flux_response(payload.get("title", "Task"))
            data["description"] = payload.get("description", "")
            self.tasks[data["id"]] = data
            resp.json.return_value = data
        elif method == "PATCH" and "/tasks/" in url:
            task_id = url.rsplit("/", 1)[-1]
            payload = kwargs.get("json", {})
            if task_id in self.tasks:
                self.tasks[task_id].update(payload)
            else:
                self.tasks[task_id] = {
                    "id": task_id, "title": "", "status": "todo", **payload,
                }
            resp.json.return_value = self.tasks[task_id]
        else:
            resp.json.return_value = {}

        return resp


# ── Integration tests ─────────────────────────────────────────────────────────

def test_full_sync_pipeline(proj_dir, sample_epics):
    mock_server = StatefulFluxMock()
    mapping: dict = {}

    with patch("httpx.request", side_effect=mock_server.handle):
        client = FluxClient()

        counts = _sync_epics(sample_epics, "proj-1", client, mapping, dry_run=False)
        assert counts["created"] == 2
        assert counts["updated"] == 0
        assert len(mock_server.tasks) == 2

        counts2 = _sync_epics(sample_epics, "proj-1", client, mapping, dry_run=False)
        assert counts2["created"] == 0
        assert counts2["updated"] == 0

        sample_epics[0].tasks[0] = ParsedTask(
            "Login", "Build login v2", ["Returns 200", "Returns 401", "Logs attempt"],
        )
        counts3 = _sync_epics(sample_epics, "proj-1", client, mapping, dry_run=False)
        assert counts3["created"] == 0
        assert counts3["updated"] == 1


def test_sync_then_webhook_generates_current_task(proj_dir, sample_epics, webhook_client):
    mock_server = StatefulFluxMock()
    mapping: dict = {}

    with patch("httpx.request", side_effect=mock_server.handle):
        client = FluxClient()
        _sync_epics(sample_epics, "proj-1", client, mapping, dry_run=False)

    task_id = list(mock_server.tasks.keys())[0]
    set_project_dir(proj_dir)

    payload = {
        "event": "task.status_changed",
        "data": {
            "task": {
                "id": task_id,
                "title": "Login",
                "status": "doing",
                "description": "Build login",
            },
            "previous": {"status": "todo"},
        },
    }
    with patch("prism.memory.store.SkillStore") as MockStore:
        MockStore.return_value.__enter__.return_value.search.return_value = []
        with patch("prism.config.load_global_config") as mock_cfg:
            mock_cfg.return_value.memory.embeddings_enabled = False
            with patch("prism.config.load_project_config") as mock_proj:
                mock_proj.return_value.name = "test-project"
                resp = webhook_client.post("/webhook/flux", json=payload)

    assert resp.status_code == 200
    current_task = proj_dir / ".prism" / "current-task.md"
    assert current_task.exists()
    assert "Login" in current_task.read_text()


def test_project_auto_creation_and_sync(proj_dir, sample_epics):
    from prism.cli.board import _ensure_flux_project, _save_flux_project_id

    mock_resp = MagicMock()
    mock_resp.json.return_value = _make_project_response("my-project")
    mock_resp.raise_for_status = MagicMock()

    mock_health = MagicMock()
    mock_health.raise_for_status = MagicMock()

    with patch("httpx.request", return_value=mock_resp):
        with patch("httpx.get", return_value=mock_health):
            _ensure_flux_project(proj_dir, "")

    import yaml
    data = yaml.safe_load(
        (proj_dir / ".prism" / "project.yaml").read_text(encoding="utf-8"),
    )
    assert data["flux_project_id"] == "proj-auto-1"

    mock_server = StatefulFluxMock()
    mapping: dict = {}
    with patch("httpx.request", side_effect=mock_server.handle):
        client = FluxClient()
        counts = _sync_epics(
            sample_epics, data["flux_project_id"], client, mapping, dry_run=False,
        )
    assert counts["created"] == 2


def test_update_task_with_changed_content(proj_dir, sample_epics):
    mock_server = StatefulFluxMock()
    mapping: dict = {}

    with patch("httpx.request", side_effect=mock_server.handle):
        client = FluxClient()
        _sync_epics(sample_epics, "proj-1", client, mapping, dry_run=False)

        original_hash = mapping["Login"]["content_hash"]
        sample_epics[0].tasks[0] = ParsedTask(
            "Login", "Redesigned login", ["New criterion"],
        )
        _sync_epics(sample_epics, "proj-1", client, mapping, dry_run=False)

        assert mapping["Login"]["content_hash"] != original_hash
        patch_calls = [c for c in mock_server.calls if c[0] == "PATCH"]
        assert len(patch_calls) == 1


def test_sync_skips_unchanged_tasks(proj_dir, sample_epics):
    mock_server = StatefulFluxMock()
    mapping: dict = {}

    with patch("httpx.request", side_effect=mock_server.handle):
        client = FluxClient()
        _sync_epics(sample_epics, "proj-1", client, mapping, dry_run=False)
        calls_after_create = len(mock_server.calls)

        _sync_epics(sample_epics, "proj-1", client, mapping, dry_run=False)
        assert len(mock_server.calls) == calls_after_create


def test_webhook_invalid_payload_returns_422(webhook_client):
    resp = webhook_client.post("/webhook/flux", json={"bad": "data"})
    assert resp.status_code == 422


def test_webhook_timeout_does_not_crash(webhook_client):
    set_project_dir(None)

    def slow_dispatch(*args, **kwargs):
        time.sleep(0.05)

    payload = {
        "event": "task.status_changed",
        "data": {
            "task": {"id": "t-slow", "title": "Slow", "status": "doing", "description": ""},
            "previous": {"status": "todo"},
        },
    }
    with patch("prism.board.webhook_listener._dispatch_transition", side_effect=slow_dispatch):
        with patch("prism.board.webhook_listener._DISPATCH_TIMEOUT", 0.01):
            resp = webhook_client.post("/webhook/flux", json=payload)
    assert resp.status_code == 200
    assert resp.json()["handled"] is True
