from __future__ import annotations

from datetime import date
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

from prism.config import GLOBAL_CONFIG_DIR, load_global_config
from prism.memory.schemas import Skill, SkillFrontmatter
from prism.memory.store import SkillStore, load_skill_from_file, save_skill_to_file

console = Console()


def _db_path() -> Path:
    return GLOBAL_CONFIG_DIR / "memory" / "index.db"


def _memory_dir() -> Path:
    return GLOBAL_CONFIG_DIR / "memory"


def _embeddings_enabled() -> bool:
    return load_global_config().memory.embeddings_enabled


@click.group(name="skill")
def skill() -> None:
    """Manage PRISM skills in memory."""


@skill.command(name="add")
@click.option("--file", "-f", "file_path", type=click.Path(exists=True), help="Load skill from .md file")
@click.option("--evaluate", is_flag=True, help="Run LLM evaluator before saving")
def add(file_path: str | None, evaluate: bool) -> None:
    """Add a skill to memory (interactive or from file)."""
    if file_path:
        _add_from_file(Path(file_path), evaluate)
    else:
        _add_interactive(evaluate)


@skill.command(name="list")
@click.option("--status", default="active", show_default=True,
              type=click.Choice(["active", "deprecated", "conflicted", "needs_review", "all"]))
def list_skills(status: str) -> None:
    """List skills in memory."""
    with SkillStore(_db_path(), _embeddings_enabled()) as store:
        skills = store.list_all(status) if status != "all" else (
            store.list_all("active") + store.list_all("deprecated") +
            store.list_all("needs_review") + store.list_all("conflicted")
        )
    _print_skill_table(skills)


@skill.command(name="search")
@click.argument("query")
@click.option("--top", default=10, show_default=True)
def search(query: str, top: int) -> None:
    """Search skills by query (FTS5 + optional embeddings)."""
    with SkillStore(_db_path(), _embeddings_enabled()) as store:
        results = store.search(query, top_k=top)
    if not results:
        console.print("[yellow]No skills found.[/yellow]")
        return
    for r in results:
        console.print(f"[bold]{r.skill.frontmatter.skill_id}[/bold] — {r.skill.title} "
                      f"[dim](score: {r.score:.2f})[/dim]")


def _add_from_file(path: Path, evaluate: bool) -> None:
    skill = load_skill_from_file(path)
    if skill is None:
        raise click.ClickException(f"Could not parse skill from {path} — check frontmatter schema")
    _persist_skill(skill, evaluate)


def _add_interactive(evaluate: bool) -> None:
    skill_id = click.prompt("Skill ID (kebab-case)")
    title = click.prompt("Title")
    skill_type = click.prompt("Type", type=click.Choice(["skill", "pattern", "gotcha", "decision"]), default="skill")
    tags_raw = click.prompt("Domain tags (comma-separated)")
    scope = click.prompt("Scope", type=click.Choice(["global", "project"]), default="global")
    project = click.prompt("Project origin", default="manual")
    content = click.prompt("Key Insight (one paragraph)")

    fm = SkillFrontmatter(
        skill_id=skill_id, type=skill_type,
        domain_tags=[t.strip() for t in tags_raw.split(",")],
        scope=scope, created=date.today(), project_origin=project,
    )
    skill_obj = Skill(frontmatter=fm, title=title, content=f"# {title}\n\n## Key Insight\n{content}")
    _persist_skill(skill_obj, evaluate)


def _persist_skill(skill: Skill, evaluate: bool) -> None:
    if evaluate:
        _run_evaluator(skill)
    mem_dir = _memory_dir()
    path = save_skill_to_file(skill, mem_dir)
    skill.file_path = path
    with SkillStore(_db_path(), _embeddings_enabled()) as store:
        store.upsert(skill)
    _maybe_git_commit(mem_dir, skill.frontmatter.skill_id)
    console.print(f"[green]✅ Skill '{skill.frontmatter.skill_id}' saved → {path}[/green]")


def _run_evaluator(skill: Skill) -> None:
    from prism.memory.evaluator import evaluate
    with SkillStore(_db_path()) as store:
        existing = [s.frontmatter.skill_id for s in store.list_all()]
    result = evaluate(skill.content, existing)
    console.print(f"[dim]Evaluator: {result.decision} — {result.reason}[/dim]")
    if result.decision == "NOOP":
        if not click.confirm("Evaluator suggests NOOP. Save anyway?"):
            raise click.Abort()


def _maybe_git_commit(mem_dir: Path, skill_id: str) -> None:
    if not load_global_config().memory.auto_commit:
        return
    try:
        import git
        repo = git.Repo(mem_dir)
        repo.index.add(["."])
        repo.index.commit(f"chore: add skill {skill_id}")
    except Exception:
        pass


def _print_skill_table(skills: list[Skill]) -> None:
    if not skills:
        console.print("[yellow]No skills found.[/yellow]")
        return
    table = Table(title=f"Skills ({len(skills)})", show_lines=False)
    table.add_column("ID", style="bold cyan")
    table.add_column("Type")
    table.add_column("Tags")
    table.add_column("Status")
    table.add_column("Uses", justify="right")
    for s in skills:
        fm = s.frontmatter
        table.add_row(fm.skill_id, fm.type, ", ".join(fm.domain_tags), fm.status, str(fm.reuse_count))
    console.print(table)
