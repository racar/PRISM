from __future__ import annotations

from pathlib import Path

import click
from rich.console import Console

from prism.spec.augmenter import augment_tasks_md, find_latest_tasks_md, is_augmented

console = Console()


@click.command()
@click.option("--file", "-f", "file_path", type=click.Path(exists=True),
              help="Specific tasks.md to augment")
@click.option("--specs-dir", default=".prism/spec", show_default=True,
              type=click.Path(), help="PRISM Spec directory")
@click.option("--force", is_flag=True, help="Re-augment even if already augmented")
def augment(file_path: str | None, specs_dir: str, force: bool) -> None:
    """Augment tasks.md with PRISM context (skills, gotchas, decisions)."""
    source = _resolve_source(file_path, specs_dir)
    if is_augmented(source.with_name("tasks.prism.md")) and not force:
        console.print("[dim]tasks.prism.md is up-to-date. Use --force to re-augment.[/dim]")
        return
    output = augment_tasks_md(source, force=force)
    console.print(f"[green]✅ Augmented → {output}[/green]")


def _resolve_source(file_path: str | None, specs_dir: str) -> Path:
    if file_path:
        return Path(file_path).resolve()
    latest = find_latest_tasks_md(Path(specs_dir))
    if latest is None:
        raise click.ClickException(
            f"No tasks.md found in {specs_dir}. Use --file to specify one."
        )
    return latest
