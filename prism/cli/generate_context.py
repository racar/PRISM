import click


@click.command(name="generate-context")
@click.option(
    "--role",
    type=click.Choice(["architect", "developer", "reviewer"]),
    help="Generate context file for this agent role",
)
def generate_context(role: str | None) -> None:
    """Generate tool-specific context file (CLAUDE.md, .cursorrules, etc.). (Available in Fase 3)"""
    raise click.ClickException("Not implemented yet (Fase 3)")
