from pathlib import Path

import pytest

from prism.project import attach_project


def test_attach_creates_prism_dir(tmp_path, tmp_prism_global):
    attach_project(tmp_path)
    assert (tmp_path / ".prism").exists()


def test_attach_creates_template_files(tmp_path, tmp_prism_global):
    attach_project(tmp_path)
    assert (tmp_path / ".prism" / "PRISM.md").exists()
    assert (tmp_path / ".prism" / "AGENTS.md").exists()
    assert (tmp_path / ".prism" / "project.yaml").exists()


def test_attach_creates_prism_spec(tmp_path, tmp_prism_global):
    attach_project(tmp_path)
    assert (tmp_path / ".prism" / "spec" / "protocol" / "AGENT.md").exists()


def test_attach_detects_existing_prism_spec(tmp_path, tmp_prism_global, capsys):
    protocol_dir = tmp_path / ".prism" / "spec" / "protocol"
    protocol_dir.mkdir(parents=True)
    (protocol_dir / "AGENT.md").write_text("# Existing protocol")
    attach_project(tmp_path)
    content = (protocol_dir / "AGENT.md").read_text()
    assert content == "# Existing protocol"


def test_attach_sets_up_prism_spec_when_missing(tmp_path, tmp_prism_global):
    attach_project(tmp_path)
    agent_md = tmp_path / ".prism" / "spec" / "protocol" / "AGENT.md"
    assert agent_md.exists()
    assert len(agent_md.read_text()) > 0


def test_attach_seeds_memory(tmp_path, tmp_prism_global):
    attach_project(tmp_path)
    skills_dir = tmp_prism_global / "memory" / "skills"
    assert skills_dir.exists()
    assert len(list(skills_dir.glob("*.md"))) == 15


def test_attach_template_contains_project_name(tmp_path, tmp_prism_global):
    attach_project(tmp_path)
    prism_md = (tmp_path / ".prism" / "PRISM.md").read_text()
    assert tmp_path.name in prism_md
