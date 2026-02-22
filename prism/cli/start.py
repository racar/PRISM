import click


@click.command()
@click.option(
    "--role",
    required=True,
    type=click.Choice(["architect", "developer", "reviewer", "memory", "optimizer"]),
    help="Agent role to launch",
)
def start(role: str) -> None:
    """Prepare context and launch an agent by role. (Available in Fase 3)"""
    raise click.ClickException("Not implemented yet (Fase 3)")
