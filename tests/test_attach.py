from pathlib import Path
from unittest.mock import patch

import pytest

from prism.project import attach_project


def test_attach_creates_prism_dir(tmp_path, tmp_prism_global):
    with patch("prism.project.check_speckit", return_value=False):
        attach_project(tmp_path)
    assert (tmp_path / ".prism").exists()


def test_attach_creates_template_files(tmp_path, tmp_prism_global):
    with patch("prism.project.check_speckit", return_value=False):
        attach_project(tmp_path)
    assert (tmp_path / ".prism" / "PRISM.md").exists()
    assert (tmp_path / ".prism" / "AGENTS.md").exists()
    assert (tmp_path / ".prism" / "project.yaml").exists()


def test_attach_detects_existing_speckit(tmp_path, tmp_prism_global):
    (tmp_path / ".specify").mkdir()
    with patch("prism.project.check_speckit", return_value=True) as mock_check:
        with patch("prism.project.run_speckit_here") as mock_run:
            attach_project(tmp_path)
    mock_run.assert_not_called()


def test_attach_runs_speckit_when_missing(tmp_path, tmp_prism_global):
    with patch("prism.project.check_speckit", return_value=True):
        with patch("prism.project.run_speckit_here", return_value=True) as mock_run:
            attach_project(tmp_path)
    mock_run.assert_called_once_with(tmp_path)


def test_attach_skips_speckit_when_not_installed(tmp_path, tmp_prism_global):
    with patch("prism.project.check_speckit", return_value=False):
        with patch("prism.project.run_speckit_here") as mock_run:
            attach_project(tmp_path)
    mock_run.assert_not_called()


def test_attach_seeds_memory(tmp_path, tmp_prism_global):
    with patch("prism.project.check_speckit", return_value=False):
        attach_project(tmp_path)
    skills_dir = tmp_prism_global / "memory" / "skills"
    assert skills_dir.exists()
    assert len(list(skills_dir.glob("*.md"))) == 7


def test_attach_template_contains_project_name(tmp_path, tmp_prism_global):
    with patch("prism.project.check_speckit", return_value=False):
        attach_project(tmp_path)
    prism_md = (tmp_path / ".prism" / "PRISM.md").read_text()
    assert tmp_path.name in prism_md
