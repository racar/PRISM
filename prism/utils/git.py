import subprocess
from pathlib import Path


def is_git_repo(path: Path) -> bool:
    result = subprocess.run(
        ["git", "rev-parse", "--is-inside-work-tree"],
        cwd=str(path), capture_output=True, text=True,
    )
    return result.returncode == 0


def git_init(path: Path) -> bool:
    result = subprocess.run(
        ["git", "init"], cwd=str(path), capture_output=True, text=True,
    )
    return result.returncode == 0


def git_add_all(path: Path) -> bool:
    result = subprocess.run(
        ["git", "add", "."], cwd=str(path), capture_output=True, text=True,
    )
    return result.returncode == 0


def git_commit(path: Path, message: str) -> bool:
    if not git_add_all(path):
        return False
    result = subprocess.run(
        ["git", "commit", "-m", message],
        cwd=str(path), capture_output=True, text=True,
    )
    return result.returncode == 0


def git_push(path: Path) -> bool:
    result = subprocess.run(
        ["git", "push"], cwd=str(path), capture_output=True, text=True,
    )
    return result.returncode == 0


def git_pull(path: Path) -> bool:
    result = subprocess.run(
        ["git", "pull"], cwd=str(path), capture_output=True, text=True,
    )
    return result.returncode == 0
