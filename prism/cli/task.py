import click


_FASE = "Fase 2"


@click.group(name="task")
def task() -> None:
    """Manage current tasks."""


@task.command(name="show")
@click.argument("task_id")
def show(task_id: str) -> None:
    """Generate current-task.md for a Flux task. (Available in Fase 2)"""
    raise click.ClickException(f"Not implemented yet ({_FASE})")
