from pathlib import Path
from unittest.mock import patch

import pytest

from prism.project import (
    create_prism_dir,
    has_existing_code,
    has_speckit,
    init_global_memory,
    init_project,
    seed_skills,
    write_prism_files,
)


def test_create_prism_dir(tmp_path):
    prism_dir = create_prism_dir(tmp_path)
    assert prism_dir.exists()
    assert prism_dir.name == ".prism"


def test_create_prism_dir_idempotent(tmp_path):
    create_prism_dir(tmp_path)
    create_prism_dir(tmp_path)
    assert (tmp_path / ".prism").exists()


def test_init_global_memory_creates_subdirs(tmp_prism_global):
    memory_dir = init_global_memory()
    assert (memory_dir / "skills").exists()
    assert (memory_dir / "gotchas").exists()
    assert (memory_dir / "decisions").exists()
    assert (memory_dir / "episodes").exists()


def test_has_speckit_false(tmp_path):
    assert has_speckit(tmp_path) is False


def test_has_speckit_true(tmp_path):
    (tmp_path / ".specify").mkdir()
    assert has_speckit(tmp_path) is True


def test_has_existing_code_false(tmp_path):
    assert has_existing_code(tmp_path) is False


def test_has_existing_code_detects_python(tmp_path):
    (tmp_path / "app.py").write_text("print('hello')")
    assert has_existing_code(tmp_path) is True


def test_has_existing_code_detects_typescript(tmp_path):
    sub = tmp_path / "src"
    sub.mkdir()
    (sub / "index.ts").write_text("console.log('hi')")
    assert has_existing_code(tmp_path) is True


def test_seed_skills_copies_all_seeds(tmp_prism_global):
    memory_dir = init_global_memory()
    count = seed_skills(memory_dir)
    assert count == 7
    skill_files = list((memory_dir / "skills").glob("*.md"))
    assert len(skill_files) == 7


def test_seed_skills_no_duplicates(tmp_prism_global):
    memory_dir = init_global_memory()
    count1 = seed_skills(memory_dir)
    count2 = seed_skills(memory_dir)
    assert count1 == 7
    assert count2 == 0


def test_seed_skills_force_overwrites(tmp_prism_global):
    memory_dir = init_global_memory()
    seed_skills(memory_dir)
    count = seed_skills(memory_dir, force=True)
    assert count == 7


def test_write_prism_files_creates_files(tmp_path):
    prism_dir = create_prism_dir(tmp_path)
    write_prism_files(prism_dir, "my-project")
    assert (prism_dir / "PRISM.md").exists()
    assert (prism_dir / "AGENTS.md").exists()
    assert (prism_dir / "project.yaml").exists()


def test_write_prism_files_contains_project_name(tmp_path):
    prism_dir = create_prism_dir(tmp_path)
    write_prism_files(prism_dir, "awesome-project")
    prism_md = (prism_dir / "PRISM.md").read_text()
    agents_md = (prism_dir / "AGENTS.md").read_text()
    project_yaml = (prism_dir / "project.yaml").read_text()
    assert "awesome-project" in prism_md
    assert "awesome-project" in agents_md
    assert "awesome-project" in project_yaml


def test_init_project_creates_full_structure(tmp_path, tmp_prism_global):
    project_dir = tmp_path / "new-project"
    with patch("prism.project.check_speckit", return_value=False):
        init_project(project_dir, skip_speckit=False)
    assert project_dir.exists()
    assert (project_dir / ".prism").exists()
    assert (project_dir / ".prism" / "PRISM.md").exists()
    assert (project_dir / ".prism" / "AGENTS.md").exists()
    assert (project_dir / ".prism" / "project.yaml").exists()


def test_init_project_seeds_memory(tmp_path, tmp_prism_global):
    project_dir = tmp_path / "new-project"
    with patch("prism.project.check_speckit", return_value=False):
        init_project(project_dir, skip_speckit=True)
    skills_dir = tmp_prism_global / "memory" / "skills"
    assert skills_dir.exists()
    assert len(list(skills_dir.glob("*.md"))) == 7


def test_init_project_creates_global_config(tmp_path, tmp_prism_global):
    project_dir = tmp_path / "new-project"
    with patch("prism.project.check_speckit", return_value=False):
        init_project(project_dir, skip_speckit=True)
    config_path = tmp_prism_global / "prism.config.yaml"
    assert config_path.exists()


def test_init_project_skip_speckit_does_not_call_specify(tmp_path, tmp_prism_global):
    project_dir = tmp_path / "my-project"
    with patch("prism.project.run_speckit_init") as mock_run:
        init_project(project_dir, skip_speckit=True)
    mock_run.assert_not_called()
