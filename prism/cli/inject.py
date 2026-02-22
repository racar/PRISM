from __future__ import annotations

from pathlib import Path

import click
from rich.console import Console

from prism.config import GLOBAL_CONFIG_DIR, load_global_config, load_project_config
from prism.memory.injector import inject_skills
from prism.memory.store import SkillStore

console = Console()


def _db_path() -> Path:
    return GLOBAL_CONFIG_DIR / "memory" / "index.db"


@click.command()
@click.option("--budget", default=4000, show_default=True, help="Max tokens to inject")
@click.option("--query", "-q", default="", help="Free-text query to focus injection")
@click.option("--project-dir", default=".", type=click.Path(), show_default=True)
def inject(budget: int, query: str, project_dir: str) -> None:
    """Inject relevant skills into .prism/injected-context.md."""
    proj_dir = Path(project_dir).resolve()
    proj_cfg = load_project_config(proj_dir)
    global_cfg = load_global_config()

    effective_query = query or proj_cfg.description or proj_cfg.name
    query_tags = set(proj_cfg.stack)
    output_path = proj_dir / ".prism" / "injected-context.md"

    embeddings = global_cfg.memory.embeddings_enabled
    with SkillStore(_db_path(), embeddings) as store:
        count = inject_skills(store, effective_query, query_tags, output_path, budget)

    console.print(f"[green]✅ {count} skills injected → {output_path}[/green]")
