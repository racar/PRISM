import click


@click.command()
@click.option("--dry-run", is_flag=True, help="Preview without creating tasks in Flux")
def sync(dry_run: bool) -> None:
    """Sync tasks.md to Flux Backlog. (Available in Fase 2)"""
    raise click.ClickException("Not implemented yet (Fase 2)")
