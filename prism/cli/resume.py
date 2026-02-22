from __future__ import annotations

from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

from prism.config import GLOBAL_CONFIG_DIR, load_global_config, load_project_config

console = Console()


@click.command()
@click.option("--project-dir", default=".", type=click.Path(), show_default=True)
def resume(project_dir: str) -> None:
    """Resume work — show project state, board status, and suggest the next agent."""
    proj_dir = Path(project_dir).resolve()
    if not (proj_dir / ".prism").exists():
        raise click.ClickException("No .prism/ found. Run: prism init or prism attach")

    proj_cfg = load_project_config(proj_dir)
    global_cfg = load_global_config()

    _print_project_overview(proj_cfg, proj_dir)
    _print_memory_stats()
    _print_board_status(proj_cfg.flux_project_id, global_cfg)
    _suggest_next_agent(proj_dir, proj_cfg)


def _print_project_overview(proj_cfg, proj_dir: Path) -> None:
    console.print(f"\n[bold]Project:[/bold] {proj_cfg.name or proj_dir.name}")
    if proj_cfg.description:
        console.print(f"[dim]{proj_cfg.description}[/dim]")
    if proj_cfg.stack:
        console.print(f"Stack: {', '.join(proj_cfg.stack)}")
    has_task = (proj_dir / ".prism" / "current-task.md").exists()
    if has_task:
        console.print("[yellow]Active task:[/yellow] .prism/current-task.md")
    console.print()


def _print_memory_stats() -> None:
    mem = GLOBAL_CONFIG_DIR / "memory"
    if not mem.exists():
        console.print("[dim]Memory: not initialized[/dim]\n")
        return
    skills = list((mem / "skills").glob("*.md")) if (mem / "skills").exists() else []
    console.print(f"[bold]Memory:[/bold] {len(skills)} skills in ~/.prism/memory/")
    db = mem / "index.db"
    console.print(f"  Index: {'✅ indexed' if db.exists() else '⚠  not indexed — run: prism index rebuild'}")
    console.print()


def _print_board_status(flux_project_id: str, global_cfg) -> None:
    if not flux_project_id:
        console.print("[dim]Board: not configured (flux_project_id not set)[/dim]\n")
        return
    try:
        from prism.board.flux_client import FluxClient
        client = FluxClient()
        if not client.healthy():
            console.print("[dim]Board: Flux not reachable[/dim]\n")
            return
        tasks = client.list_tasks(flux_project_id)
        _print_task_table(tasks)
    except Exception as exc:
        console.print(f"[dim]Board: could not fetch tasks ({exc})[/dim]\n")


def _print_task_table(tasks: list) -> None:
    table = Table(title="Board", show_lines=False)
    table.add_column("Status")
    table.add_column("Count", justify="right")
    counts: dict[str, int] = {}
    for t in tasks:
        counts[t.status] = counts.get(t.status, 0) + 1
    for status in ("todo", "doing", "review", "done"):
        n = counts.get(status, 0)
        color = "green" if n and status == "doing" else "dim"
        table.add_row(f"[{color}]{status}[/{color}]", str(n))
    console.print(table)
    console.print()


def _suggest_next_agent(proj_dir: Path, proj_cfg) -> None:
    has_task = (proj_dir / ".prism" / "current-task.md").exists()
    role = "developer" if has_task else "architect"
    console.print(f"[bold]Suggested next step:[/bold] [cyan]prism start --role {role}[/cyan]")
    _check_memory_sync()


def _check_memory_sync() -> None:
    mem = GLOBAL_CONFIG_DIR / "memory"
    try:
        import git
        repo = git.Repo(mem)
        if repo.is_dirty(untracked_files=True):
            console.print("[yellow]⚠  Memory has uncommitted changes — run: prism memory push[/yellow]")
    except Exception:
        pass
