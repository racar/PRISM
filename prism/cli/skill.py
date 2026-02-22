import click


_FASE = "Fase 1"


@click.group(name="skill")
def skill() -> None:
    """Manage PRISM skills in memory."""


@skill.command(name="add")
@click.option("--file", "-f", "file_path", type=click.Path(), help="Load skill from file")
def add(file_path: str | None) -> None:
    """Add a skill to memory. (Available in Fase 1)"""
    raise click.ClickException(f"Not implemented yet ({_FASE})")


@skill.command(name="list")
@click.option("--status", default="active", show_default=True)
def list_skills(status: str) -> None:
    """List skills in memory. (Available in Fase 1)"""
    raise click.ClickException(f"Not implemented yet ({_FASE})")


@skill.command(name="search")
@click.argument("query")
def search(query: str) -> None:
    """Search skills by query. (Available in Fase 1)"""
    raise click.ClickException(f"Not implemented yet ({_FASE})")
