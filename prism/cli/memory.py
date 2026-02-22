import click


_FASE = "Fase 1"


@click.group(name="memory")
def memory() -> None:
    """Manage PRISM memory Git sync."""


@memory.command(name="push")
def push() -> None:
    """Commit and push memory to Git remote. (Available in Fase 1)"""
    raise click.ClickException(f"Not implemented yet ({_FASE})")


@memory.command(name="pull")
def pull() -> None:
    """Pull memory updates from Git remote. (Available in Fase 1)"""
    raise click.ClickException(f"Not implemented yet ({_FASE})")


@memory.command(name="status")
def status() -> None:
    """Show pending memory changes. (Available in Fase 1)"""
    raise click.ClickException(f"Not implemented yet ({_FASE})")
