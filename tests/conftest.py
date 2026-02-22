import pytest
from pathlib import Path


@pytest.fixture
def tmp_project(tmp_path: Path) -> Path:
    project_dir = tmp_path / "test-project"
    project_dir.mkdir()
    return project_dir


@pytest.fixture
def tmp_prism_global(tmp_path: Path, monkeypatch) -> Path:
    global_dir = tmp_path / "prism_global"
    global_dir.mkdir()
    monkeypatch.setattr("prism.config.GLOBAL_CONFIG_DIR", global_dir)
    monkeypatch.setattr("prism.config.GLOBAL_CONFIG_PATH", global_dir / "prism.config.yaml")
    monkeypatch.setattr("prism.project.GLOBAL_CONFIG_DIR", global_dir)
    monkeypatch.setattr("prism.project.GLOBAL_CONFIG_PATH", global_dir / "prism.config.yaml")
    return global_dir
