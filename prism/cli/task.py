from __future__ import annotations

from pathlib import Path

import click
from rich.console import Console

console = Console()


@click.group(name="task")
def task() -> None:
    """Manage current tasks."""


@task.command(name="show")
@click.argument("task_id")
@click.option("--project-dir", default=".", type=click.Path(), show_default=True)
def show(task_id: str, project_dir: str) -> None:
    """Fetch a Flux task and generate .prism/current-task.md."""
    from prism.board.flux_client import FluxClient
    from prism.board.task_mapper import generate_current_task_md

    client = FluxClient()
    if not client.healthy():
        raise click.ClickException("Flux is not reachable. Run: prism board setup")

    flux_task = client.get_task(task_id)
    proj_dir = Path(project_dir).resolve()
    output = generate_current_task_md(flux_task, proj_dir)
    console.print(f"[green]✅ current-task.md generated → {output}[/green]")
    console.print(f"\n[bold]{flux_task.title}[/bold]")
    console.print(f"Status: {flux_task.status}")
