from pathlib import Path

import click

from prism.project import init_project


@click.command()
@click.argument("name", required=False)
@click.option("--no-embeddings", is_flag=True, help="Use FTS5 only (available in Fase 1)")
def init(name: str | None, no_embeddings: bool) -> None:
    """Initialize a new PRISM project."""
    project_dir = Path.cwd() / name if name else Path.cwd()
    init_project(project_dir)
