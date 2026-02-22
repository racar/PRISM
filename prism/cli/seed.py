import click
from rich.console import Console

from prism.project import init_global_memory, seed_skills

console = Console()


@click.command()
@click.option("--force", is_flag=True, help="Re-seed even if skills already exist")
def seed(force: bool) -> None:
    """Load seed skills into ~/.prism/memory/skills/."""
    memory_dir = init_global_memory()
    count = seed_skills(memory_dir, force=force)
    console.print(f"[green]✅ Loaded {count} seed skills[/green]")
