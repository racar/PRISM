import click


_FASE = "Fase 2"


@click.group(name="board")
def board() -> None:
    """Manage Flux Kanban board integration."""


@board.command(name="setup")
def setup() -> None:
    """Launch Flux via Docker and register MCP. (Available in Fase 2)"""
    raise click.ClickException(f"Not implemented yet ({_FASE})")


@board.command(name="listen")
@click.option("--daemon", is_flag=True, help="Run in background")
@click.option("--port", default=8765, show_default=True)
def listen(daemon: bool, port: int) -> None:
    """Start webhook listener for Flux events. (Available in Fase 2)"""
    raise click.ClickException(f"Not implemented yet ({_FASE})")


@board.command(name="stop")
def stop() -> None:
    """Stop the webhook listener process. (Available in Fase 2)"""
    raise click.ClickException(f"Not implemented yet ({_FASE})")


@board.command(name="status")
def status() -> None:
    """Show listener status and last event. (Available in Fase 2)"""
    raise click.ClickException(f"Not implemented yet ({_FASE})")
