from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from unittest.mock import MagicMock, patch

import httpx
import pytest
from fastapi.testclient import TestClient

from prism.board.flux_client import FluxClient, Task, Epic
from prism.board.task_mapper import (
    ParsedEpic, ParsedTask, _parse_epics, _parse_criteria,
    generate_current_task_md,
)
from prism.board.webhook_listener import app, set_project_dir
from prism.cli.sync import (
    _task_content_hash, _task_changed, _normalize_mapping, _sync_epics,
)
from prism.memory.schemas import Skill, SkillFrontmatter
from prism.memory.store import SkillStore, save_skill_to_file


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def webhook_client():
    return TestClient(app)


@pytest.fixture
def flux_client():
    return FluxClient()


@pytest.fixture
def sample_tasks_md(tmp_path) -> Path:
    content = """\
# Feature: Auth

## Epic: User Authentication

This epic covers login and registration.

### Task 1: Implement login endpoint

Create a POST /auth/login endpoint that validates credentials.

**Acceptance Criteria:**
- [ ] Returns 200 with JWT on valid credentials
- [ ] Returns 401 on invalid credentials
- [ ] Rate limited to 10 req/min

### Task 2: Implement registration

Create a POST /auth/register endpoint.

**Acceptance Criteria:**
- [ ] Validates email format
- [ ] Hashes password with bcrypt
"""
    p = tmp_path / "tasks.md"
    p.write_text(content)
    return p


@pytest.fixture
def mem_dir(tmp_path) -> Path:
    for sub in ("skills", "gotchas", "decisions"):
        (tmp_path / sub).mkdir()
    return tmp_path


@pytest.fixture
def db_with_skills(tmp_path, mem_dir):
    db = tmp_path / "index.db"
    fm = SkillFrontmatter(
        skill_id="jwt-auth", type="skill",
        domain_tags=["auth", "jwt", "security"],
        scope="global", created=date(2026, 2, 21),
        project_origin="test",
    )
    skill = Skill(fm, "JWT Authentication Pattern", "# JWT Auth\n\nUse RS256 for production.", None)
    skill.file_path = save_skill_to_file(skill, mem_dir)
    with SkillStore(db) as store:
        store.upsert(skill)
    return db


# ── 2.2 FluxClient ────────────────────────────────────────────────────────────

def test_flux_client_create_task(flux_client):
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"id": "t-1", "title": "Login endpoint", "status": "todo", "description": "body"}
    mock_resp.raise_for_status = MagicMock()
    with patch("httpx.request", return_value=mock_resp):
        task = flux_client.create_task("proj-1", "Login endpoint", "body")
    assert task.id == "t-1"
    assert task.title == "Login endpoint"
    assert task.status == "todo"


def test_flux_client_create_epic(flux_client):
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"id": "e-1", "title": "Auth Epic", "description": "desc"}
    mock_resp.raise_for_status = MagicMock()
    with patch("httpx.request", return_value=mock_resp):
        epic = flux_client.create_epic("proj-1", "Auth Epic", "desc")
    assert epic.id == "e-1"
    assert epic.title == "Auth Epic"


def test_flux_client_move_task(flux_client):
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"id": "t-1", "title": "Login", "status": "doing"}
    mock_resp.raise_for_status = MagicMock()
    with patch("httpx.request", return_value=mock_resp):
        task = flux_client.move_task("t-1", "doing")
    assert task.status == "doing"


def test_flux_client_retries_on_failure(flux_client):
    call_count = 0
    def flaky(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise httpx.ConnectError("timeout")
        m = MagicMock()
        m.json.return_value = {"id": "t-1", "title": "T", "status": "todo"}
        m.raise_for_status = MagicMock()
        return m
    with patch("httpx.request", side_effect=flaky):
        with patch("time.sleep"):
            task = flux_client.create_task("proj-1", "T")
    assert task.id == "t-1"
    assert call_count == 3


def test_flux_client_raises_after_max_retries(flux_client):
    with patch("httpx.request", side_effect=httpx.ConnectError("down")):
        with patch("time.sleep"):
            with pytest.raises(RuntimeError, match="failed after retries"):
                flux_client.create_task("proj-1", "T")


def test_flux_healthy_true(flux_client):
    m = MagicMock()
    m.raise_for_status = MagicMock()
    with patch("httpx.get", return_value=m):
        assert flux_client.healthy() is True


def test_flux_healthy_false_when_down(flux_client):
    with patch("httpx.get", side_effect=httpx.ConnectError("down")):
        assert flux_client.healthy() is False


# ── 2.3 Augmenter ─────────────────────────────────────────────────────────────

def test_augment_adds_prism_context(sample_tasks_md, tmp_path, mem_dir):
    from prism.spec.augmenter import augment_tasks_md, is_augmented
    db = tmp_path / "index.db"
    fm = SkillFrontmatter(
        skill_id="jwt-auth", type="skill",
        domain_tags=["auth", "jwt"],
        scope="global", created=date(2026, 2, 21),
        project_origin="test",
    )
    skill = Skill(fm, "JWT Auth", "# JWT\n\nUse RS256.", None)
    skill.file_path = save_skill_to_file(skill, mem_dir)
    with SkillStore(db) as store:
        store.upsert(skill)

    with patch("prism.spec.augmenter.GLOBAL_CONFIG_DIR", tmp_path):
        with patch("prism.spec.augmenter.load_global_config") as mock_cfg:
            mock_cfg.return_value.memory.embeddings_enabled = False
            with patch("prism.spec.augmenter.SkillStore") as MockStore:
                MockStore.return_value.__enter__.return_value.search.return_value = [
                    MagicMock(skill=skill)
                ]
                output = augment_tasks_md(sample_tasks_md)

    assert output.exists()
    content = output.read_text()
    assert "<!-- PRISM AUGMENTED -->" in content
    assert "PRISM Context" in content


def test_augment_skips_if_already_augmented(sample_tasks_md):
    from prism.spec.augmenter import augment_tasks_md, is_augmented
    output = sample_tasks_md.with_name("tasks.prism.md")
    output.write_text("<!-- PRISM AUGMENTED -->\nsome content")
    result = augment_tasks_md(sample_tasks_md, force=False)
    assert result == output


def test_augment_force_overwrites(sample_tasks_md, tmp_path, mem_dir):
    from prism.spec.augmenter import augment_tasks_md
    output = sample_tasks_md.with_name("tasks.prism.md")
    output.write_text("<!-- PRISM AUGMENTED -->\nold content")
    with patch("prism.spec.augmenter.GLOBAL_CONFIG_DIR", tmp_path):
        with patch("prism.spec.augmenter.load_global_config") as mock_cfg:
            mock_cfg.return_value.memory.embeddings_enabled = False
            with patch("prism.spec.augmenter.SkillStore") as MockStore:
                MockStore.return_value.__enter__.return_value.search.return_value = []
                result = augment_tasks_md(sample_tasks_md, force=True)
    assert "old content" not in result.read_text()


# ── 2.4 Sync / task_mapper ────────────────────────────────────────────────────

def test_parse_tasks_md_extracts_epics(sample_tasks_md):
    epics = _parse_epics(sample_tasks_md.read_text())
    assert len(epics) == 1
    assert "Auth" in epics[0].title


def test_parse_tasks_md_extracts_tasks(sample_tasks_md):
    epics = _parse_epics(sample_tasks_md.read_text())
    assert len(epics[0].tasks) == 2
    titles = [t.title for t in epics[0].tasks]
    assert any("login" in t.lower() for t in titles)


def test_parse_criteria_extracts_checkboxes():
    body = "- [ ] Returns 200\n- [ ] Returns 401\n- [x] Rate limited\n"
    criteria = _parse_criteria(body)
    assert len(criteria) == 3
    assert "Returns 200" in criteria


def test_sync_maps_tasks_without_duplicates(sample_tasks_md, tmp_path):
    from prism.cli.sync import _sync_epics, _load_mapping
    epics = _parse_epics(sample_tasks_md.read_text())
    mapping: dict = {}

    mock_client = MagicMock()
    mock_client.create_epic.return_value = MagicMock(id="e-1")
    mock_client.create_task.side_effect = [
        MagicMock(id="t-1"), MagicMock(id="t-2"),
    ]

    counts = _sync_epics(epics, "proj-1", mock_client, mapping, dry_run=False)
    assert counts["created"] == 2

    counts_again = _sync_epics(epics, "proj-1", mock_client, mapping, dry_run=False)
    assert counts_again["created"] == 0


# ── 2.5 Webhook listener ──────────────────────────────────────────────────────

def test_webhook_health(webhook_client):
    resp = webhook_client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_webhook_ignores_unknown_events(webhook_client):
    payload = {"event": "unknown.event", "data": {"task": {"id": "t-1", "title": "T", "status": "todo"}, "previous": {}}}
    resp = webhook_client.post("/webhook/flux", json=payload)
    assert resp.status_code == 200
    assert resp.json()["handled"] is False


def test_webhook_handles_status_changed(webhook_client):
    payload = {
        "event": "task.status_changed",
        "data": {
            "task": {"id": "t-1", "title": "Login", "status": "doing", "description": "body"},
            "previous": {"status": "todo"},
        },
    }
    with patch("prism.board.webhook_listener._on_task_started") as mock_started:
        resp = webhook_client.post("/webhook/flux", json=payload)
    assert resp.status_code == 200
    assert resp.json()["handled"] is True
    mock_started.assert_called_once()


def test_webhook_todo_to_doing_generates_current_task_md(tmp_path, webhook_client):
    set_project_dir(tmp_path)
    (tmp_path / ".prism").mkdir()
    payload = {
        "event": "task.status_changed",
        "data": {
            "task": {"id": "t-42", "title": "Implement JWT login", "status": "doing", "description": "Build auth"},
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
    current_task = tmp_path / ".prism" / "current-task.md"
    assert current_task.exists()
    content = current_task.read_text()
    assert "t-42" in content
    assert "Implement JWT login" in content
    assert "What to Build" in content
    assert "Definition of Done" in content


# ── 2.6 current-task.md format (DT-4) ────────────────────────────────────────

def test_current_task_md_has_all_sections(tmp_path):
    task = MagicMock()
    task.id = "TASK-7"
    task.title = "Add rate limiting"
    task.description = "Protect the login endpoint"
    task.epic_id = "EPIC-1"
    task.criteria = ["Returns 429 on excess calls"]

    with patch("prism.memory.store.SkillStore") as MockStore:
        MockStore.return_value.__enter__.return_value.search.return_value = []
        with patch("prism.config.load_global_config") as mock_cfg:
            mock_cfg.return_value.memory.embeddings_enabled = False
            with patch("prism.config.load_project_config") as mock_proj:
                mock_proj.return_value.name = "my-project"
                path = generate_current_task_md(task, tmp_path)

    content = path.read_text()
    assert "# Current Task: TASK-7" in content
    assert "## What to Build" in content
    assert "## Acceptance Criteria" in content
    assert "## PRISM Context" in content
    assert "## Definition of Done" in content
    assert "## Output" in content


# ── 2.7 update_task / content-hash / normalize ────────────────────────────────

def test_flux_client_update_task(flux_client):
    mock_resp = MagicMock()
    mock_resp.json.return_value = {
        "id": "t-1", "title": "Updated", "status": "todo", "description": "new body",
    }
    mock_resp.raise_for_status = MagicMock()
    with patch("httpx.request", return_value=mock_resp):
        task = flux_client.update_task("t-1", title="Updated", description="new body")
    assert task.title == "Updated"
    assert task.description == "new body"


def test_task_content_hash_deterministic():
    task = ParsedTask("Login", "Build login", ["Returns 200", "Returns 401"])
    h1 = _task_content_hash(task)
    h2 = _task_content_hash(task)
    assert h1 == h2
    assert len(h1) == 16


def test_task_content_hash_changes_with_content():
    t1 = ParsedTask("Login", "Build login", ["Returns 200"])
    t2 = ParsedTask("Login", "Build login v2", ["Returns 200"])
    assert _task_content_hash(t1) != _task_content_hash(t2)


def test_task_changed_detects_difference():
    task = ParsedTask("Login", "Build login", ["Returns 200"])
    mapping = {"Login": {"flux_id": "t-1", "content_hash": "wrong"}}
    assert _task_changed(task, mapping) is True


def test_task_changed_returns_false_when_same():
    task = ParsedTask("Login", "Build login", ["Returns 200"])
    h = _task_content_hash(task)
    mapping = {"Login": {"flux_id": "t-1", "content_hash": h}}
    assert _task_changed(task, mapping) is False


def test_normalize_mapping_migrates_strings():
    mapping = {"Login": "t-1", "__epic__Auth": "e-1"}
    _normalize_mapping(mapping)
    assert mapping["Login"] == {"flux_id": "t-1", "content_hash": ""}
    assert mapping["__epic__Auth"] == "e-1"


def test_sync_epics_returns_dict_counts(sample_tasks_md):
    epics = _parse_epics(sample_tasks_md.read_text())
    mapping: dict = {}
    mock_client = MagicMock()
    mock_client.create_epic.return_value = MagicMock(id="e-1")
    mock_client.create_task.side_effect = [
        MagicMock(id="t-1"), MagicMock(id="t-2"),
    ]
    counts = _sync_epics(epics, "proj-1", mock_client, mapping, dry_run=False)
    assert isinstance(counts, dict)
    assert counts["created"] == 2
    assert counts["updated"] == 0
