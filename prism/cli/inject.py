import click


@click.command()
@click.option("--budget", default=4000, show_default=True, help="Max tokens to inject")
def inject(budget: int) -> None:
    """Inject relevant skills into .prism/injected-context.md. (Available in Fase 1)"""
    raise click.ClickException("Not implemented yet (Fase 1)")
