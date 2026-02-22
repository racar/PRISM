import click


@click.group(name="index")
def index() -> None:
    """Manage the PRISM skill index."""


@index.command(name="rebuild")
def rebuild() -> None:
    """Rebuild the SQLite FTS5 index from markdown files. (Available in Fase 1)"""
    raise click.ClickException("Not implemented yet (Fase 1)")
