from __future__ import annotations

from datetime import date
from pathlib import Path

import click
from rich.console import Console

from prism.config import GLOBAL_CONFIG_DIR, load_global_config

console = Console()


def _memory_dir() -> Path:
    return GLOBAL_CONFIG_DIR / "memory"


def _ensure_git_repo(mem_dir: Path) -> bool:
    try:
        import git
        git.Repo(mem_dir)
        return True
    except Exception:
        return False


def _get_repo(mem_dir: Path):
    import git
    return git.Repo(mem_dir)


@click.group(name="memory")
def memory() -> None:
    """Manage PRISM memory Git sync."""


@memory.command(name="push")
@click.option("--message", "-m", default="", help="Custom commit message")
def push(message: str) -> None:
    """Commit and push memory to Git remote."""
    mem_dir = _memory_dir()
    if not _ensure_git_repo(mem_dir):
        raise click.ClickException(
            "Memory dir is not a git repo. Run: git -C ~/.prism/memory init"
        )
    cfg = load_global_config()
    if not cfg.memory.git_remote:
        raise click.ClickException(
            "git_remote not set in ~/.prism/prism.config.yaml. "
            "Set memory.git_remote to your remote URL."
        )
    msg = message or f"chore: memory update {date.today()}"
    _commit_and_push(mem_dir, msg)


@memory.command(name="pull")
def pull() -> None:
    """Pull memory updates from Git remote."""
    mem_dir = _memory_dir()
    if not _ensure_git_repo(mem_dir):
        raise click.ClickException("Memory dir is not a git repo.")
    try:
        repo = _get_repo(mem_dir)
        repo.remotes.origin.pull()
        console.print("[green]✅ Memory pulled from remote[/green]")
    except Exception as exc:
        raise click.ClickException(f"Pull failed: {exc}")


@memory.command(name="status")
def status() -> None:
    """Show pending memory changes."""
    mem_dir = _memory_dir()
    if not _ensure_git_repo(mem_dir):
        console.print("[yellow]Memory dir is not a git repo.[/yellow]")
        return
    repo = _get_repo(mem_dir)
    changed = [item.a_path for item in repo.index.diff(None)]
    untracked = repo.untracked_files
    console.print(f"[bold]Memory status:[/bold] {mem_dir}")
    console.print(f"  Modified : {len(changed)}")
    console.print(f"  Untracked: {len(untracked)}")
    for f in changed + untracked:
        console.print(f"  [dim]  {f}[/dim]")


def _commit_and_push(mem_dir: Path, message: str) -> None:
    try:
        repo = _get_repo(mem_dir)
        repo.index.add(["."])
        if not repo.is_dirty(index=True):
            console.print("[dim]Nothing to commit.[/dim]")
            return
        repo.index.commit(message)
        repo.remotes.origin.push()
        console.print(f"[green]✅ Memory pushed: {message}[/green]")
    except Exception as exc:
        raise click.ClickException(f"Push failed: {exc}")
