from pathlib import Path

import click

from prism.project import attach_project


@click.command()
@click.argument("directory", required=False, default=".")
def attach(directory: str) -> None:
    """Attach PRISM to an existing project directory."""
    project_dir = Path(directory).resolve()
    if not project_dir.exists():
        raise click.ClickException(f"Directory '{directory}' does not exist")
    attach_project(project_dir)
