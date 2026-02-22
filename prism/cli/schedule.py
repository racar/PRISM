import click


_FASE = "Fase 4"


@click.group(name="schedule")
def schedule() -> None:
    """Manage the weekly optimizer scheduler."""


@schedule.command(name="enable")
def enable() -> None:
    """Install weekly cron job for prism optimize --auto. (Available in Fase 4)"""
    raise click.ClickException(f"Not implemented yet ({_FASE})")


@schedule.command(name="disable")
def disable() -> None:
    """Remove the optimizer cron job. (Available in Fase 4)"""
    raise click.ClickException(f"Not implemented yet ({_FASE})")
