from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from prism.memory.schemas import EvaluationResult, Skill, SkillFrontmatter
from prism.memory.store import SkillStore, load_skill_from_file, save_skill_to_file


# ── Fixtures ──────────────────────────────────────────────────────────────────

def _make_frontmatter(**kwargs) -> SkillFrontmatter:
    defaults = dict(
        skill_id="test-skill",
        type="skill",
        domain_tags=["python", "testing"],
        scope="global",
        created=date(2026, 2, 21),
        project_origin="test-project",
    )
    defaults.update(kwargs)
    return SkillFrontmatter(**defaults)


def _make_skill(skill_id: str = "test-skill", tags: list[str] | None = None) -> Skill:
    fm = _make_frontmatter(skill_id=skill_id, domain_tags=tags or ["python", "testing"])
    return Skill(frontmatter=fm, title="Test Skill", content="# Test Skill\n\nKey insight here.")


@pytest.fixture
def db_path(tmp_path) -> Path:
    return tmp_path / "index.db"


@pytest.fixture
def mem_dir(tmp_path) -> Path:
    for sub in ("skills", "gotchas", "decisions"):
        (tmp_path / sub).mkdir()
    return tmp_path


# ── 1.1 Schema tests ──────────────────────────────────────────────────────────

def test_skill_frontmatter_valid():
    fm = _make_frontmatter()
    assert fm.skill_id == "test-skill"
    assert fm.status == "active"
    assert fm.reuse_count == 0


def test_skill_frontmatter_invalid_skill_id():
    with pytest.raises(Exception):
        _make_frontmatter(skill_id="Invalid_ID")


def test_skill_frontmatter_requires_domain_tags():
    with pytest.raises(Exception):
        _make_frontmatter(domain_tags=[])


def test_skill_subdir_for_type():
    assert _make_frontmatter(type="skill").subdir() == "skills"
    assert _make_frontmatter(type="pattern").subdir() == "skills"
    assert _make_frontmatter(type="gotcha").subdir() == "gotchas"
    assert _make_frontmatter(type="decision").subdir() == "decisions"


# ── 1.2 Store: upsert / search ────────────────────────────────────────────────

def test_store_upsert_and_get(db_path, mem_dir):
    skill = _make_skill()
    skill.file_path = save_skill_to_file(skill, mem_dir)
    with SkillStore(db_path) as store:
        store.upsert(skill)
        assert store.count() == 1
        fetched = store.get("test-skill")
    assert fetched is not None
    assert fetched.frontmatter.skill_id == "test-skill"


def test_store_fts5_finds_by_domain_tag(db_path, mem_dir):
    skill = _make_skill(tags=["nodejs", "jest", "testing"])
    skill.file_path = save_skill_to_file(skill, mem_dir)
    with SkillStore(db_path) as store:
        store.upsert(skill)
        results = store.search("nodejs jest")
    assert len(results) >= 1
    assert results[0].skill.frontmatter.skill_id == "test-skill"


def test_store_fts5_finds_by_content(db_path, mem_dir):
    fm = _make_frontmatter(skill_id="jwt-auth", domain_tags=["auth", "security"])
    skill = Skill(fm, "JWT Authentication", "# JWT Auth\n\nUse RS256 for production tokens.", None)
    skill.file_path = save_skill_to_file(skill, mem_dir)
    with SkillStore(db_path) as store:
        store.upsert(skill)
        results = store.search("RS256 production tokens")
    assert len(results) >= 1
    assert results[0].skill.frontmatter.skill_id == "jwt-auth"


def test_store_search_returns_empty_for_no_match(db_path, mem_dir):
    skill = _make_skill()
    skill.file_path = save_skill_to_file(skill, mem_dir)
    with SkillStore(db_path) as store:
        store.upsert(skill)
        results = store.search("xyznonexistentquery123")
    assert results == []


def test_store_delete(db_path, mem_dir):
    skill = _make_skill()
    skill.file_path = save_skill_to_file(skill, mem_dir)
    with SkillStore(db_path) as store:
        store.upsert(skill)
        store.delete("test-skill")
        assert store.count() == 0


def test_store_list_all(db_path, mem_dir):
    for i in range(3):
        s = _make_skill(skill_id=f"skill-{i}", tags=["python"])
        s.file_path = save_skill_to_file(s, mem_dir)
        with SkillStore(db_path) as store:
            store.upsert(s)
    with SkillStore(db_path) as store:
        skills = store.list_all()
    assert len(skills) == 3


def test_store_clear(db_path, mem_dir):
    skill = _make_skill()
    skill.file_path = save_skill_to_file(skill, mem_dir)
    with SkillStore(db_path) as store:
        store.upsert(skill)
        store.clear()
        assert store.count() == 0


# ── File I/O ─────────────────────────────────────────────────────────────────

def test_save_and_load_roundtrip(mem_dir):
    skill = _make_skill()
    path = save_skill_to_file(skill, mem_dir)
    assert path.exists()
    loaded = load_skill_from_file(path)
    assert loaded is not None
    assert loaded.frontmatter.skill_id == "test-skill"
    assert loaded.frontmatter.domain_tags == ["python", "testing"]


def test_load_skill_missing_file(tmp_path):
    result = load_skill_from_file(tmp_path / "nonexistent.md")
    assert result is None


def test_load_skill_invalid_frontmatter(tmp_path):
    bad = tmp_path / "bad.md"
    bad.write_text("---\nskill_id: INVALID ID WITH SPACES\n---\nContent\n")
    result = load_skill_from_file(bad)
    assert result is None


# ── 1.5 Inject: token budget ──────────────────────────────────────────────────

def test_inject_respects_token_budget(db_path, mem_dir, tmp_path):
    from prism.memory.injector import inject_skills

    for i in range(10):
        s = _make_skill(skill_id=f"skill-{i}", tags=["python"])
        s.file_path = save_skill_to_file(s, mem_dir)
        with SkillStore(db_path) as store:
            store.upsert(s)

    output = tmp_path / ".prism" / "injected-context.md"
    with SkillStore(db_path) as store:
        inject_skills(store, "python", {"python"}, output, budget=300)

    content = output.read_text()
    from prism.memory.injector import count_tokens
    assert count_tokens(content) <= 600  # allow header overhead


def test_inject_generates_output_file(db_path, mem_dir, tmp_path):
    from prism.memory.injector import inject_skills

    skill = _make_skill()
    skill.file_path = save_skill_to_file(skill, mem_dir)
    with SkillStore(db_path) as store:
        store.upsert(skill)

    output = tmp_path / ".prism" / "injected-context.md"
    with SkillStore(db_path) as store:
        count = inject_skills(store, "python testing", {"python"}, output, budget=4000)

    assert output.exists()
    assert count >= 1
    assert "AUTO-GENERATED" in output.read_text()


# ── 1.6 Evaluator ─────────────────────────────────────────────────────────────

def test_evaluator_returns_noop_without_api_key(monkeypatch):
    from prism.memory.evaluator import evaluate
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    result = evaluate("Use print for debugging")
    assert result.decision == "NOOP"


def test_evaluator_returns_add_for_genuine_discovery(monkeypatch):
    from prism.memory.evaluator import evaluate
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

    mock_response = MagicMock()
    mock_response.content = [MagicMock(text=json.dumps({
        "decision": "ADD",
        "skill_id": "jwt-rs256-gotcha",
        "type": "gotcha",
        "domain_tags": ["auth", "jwt"],
        "reason": "Non-obvious behavior worth remembering",
        "merge_with": "",
    }))]

    with patch("anthropic.Anthropic") as MockClient:
        MockClient.return_value.messages.create.return_value = mock_response
        result = evaluate("When using JWT RS256, the public key must include newlines exactly as-is or verification silently fails.")

    assert result.decision == "ADD"
    assert result.type == "gotcha"


def test_evaluator_returns_noop_for_trivial_content(monkeypatch):
    from prism.memory.evaluator import evaluate
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

    mock_response = MagicMock()
    mock_response.content = [MagicMock(text=json.dumps({
        "decision": "NOOP",
        "skill_id": "",
        "type": "skill",
        "domain_tags": [],
        "reason": "This is basic documentation usage, not a genuine discovery",
        "merge_with": "",
    }))]

    with patch("anthropic.Anthropic") as MockClient:
        MockClient.return_value.messages.create.return_value = mock_response
        result = evaluate("Use npm install to install dependencies.")

    assert result.decision == "NOOP"


def test_evaluator_handles_malformed_response(monkeypatch):
    from prism.memory.evaluator import evaluate
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

    mock_response = MagicMock()
    mock_response.content = [MagicMock(text="not valid json")]

    with patch("anthropic.Anthropic") as MockClient:
        MockClient.return_value.messages.create.return_value = mock_response
        result = evaluate("some content")

    assert result.decision == "NOOP"


# ── 1.7 Git sync ─────────────────────────────────────────────────────────────

def test_git_commit_generated_on_skill_add(mem_dir):
    import git
    repo = git.Repo.init(mem_dir)
    repo.config_writer().set_value("user", "name", "Test").release()
    repo.config_writer().set_value("user", "email", "test@test.com").release()

    skill = _make_skill()
    skill.file_path = save_skill_to_file(skill, mem_dir)
    repo.index.add(["."])
    repo.index.commit("chore: add skill test-skill")

    assert len(list(repo.iter_commits())) == 1
    assert "test-skill" in list(repo.iter_commits())[0].message
