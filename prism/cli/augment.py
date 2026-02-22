import click


@click.command()
@click.option("--file", "-f", "file_path", type=click.Path(), help="Specific tasks.md to augment")
@click.option("--force", is_flag=True, help="Re-augment even if already augmented")
def augment(file_path: str | None, force: bool) -> None:
    """Augment tasks.md with PRISM context (skills, gotchas, decisions). (Available in Fase 2)"""
    raise click.ClickException("Not implemented yet (Fase 2)")
