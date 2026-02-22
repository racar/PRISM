from __future__ import annotations

from pathlib import Path

import click
import yaml
from rich.console import Console

from prism.config import GLOBAL_CONFIG_DIR, load_global_config
from prism.memory.store import SkillStore, load_skill_from_file

console = Console()

_MEMORY_SUBDIRS = ("skills", "gotchas", "decisions")


def _db_path() -> Path:
    return GLOBAL_CONFIG_DIR / "memory" / "index.db"


def _memory_dir() -> Path:
    return GLOBAL_CONFIG_DIR / "memory"


@click.group(name="index")
def index() -> None:
    """Manage the PRISM skill index."""


@index.command(name="rebuild")
@click.option("--verbose", "-v", is_flag=True)
def rebuild(verbose: bool) -> None:
    """Rebuild SQLite FTS5 index from all markdown files in ~/.prism/memory/."""
    mem_dir = _memory_dir()
    embeddings = load_global_config().memory.embeddings_enabled
    valid, invalid = [], []

    with SkillStore(_db_path(), embeddings) as store:
        store.clear()
        for md_file in _iter_skill_files(mem_dir):
            skill = load_skill_from_file(md_file)
            if skill is None:
                invalid.append(md_file)
                if verbose:
                    console.print(f"[yellow]  ⚠ invalid frontmatter: {md_file}[/yellow]")
                continue
            skill.file_path = md_file
            store.upsert(skill)
            valid.append(skill)
            if verbose:
                console.print(f"  ✓ {skill.frontmatter.skill_id}")

    _write_index_yaml(mem_dir, valid)
    console.print(f"[green]✅ Index rebuilt — {len(valid)} skills indexed[/green]")
    if invalid:
        console.print(f"[yellow]⚠  {len(invalid)} files with invalid frontmatter (use --verbose to list)[/yellow]")


def _iter_skill_files(mem_dir: Path):
    for subdir in _MEMORY_SUBDIRS:
        yield from (mem_dir / subdir).glob("*.md")


def _write_index_yaml(mem_dir: Path, skills: list) -> None:
    by_type: dict[str, int] = {}
    by_status: dict[str, int] = {}
    for s in skills:
        by_type[s.frontmatter.type] = by_type.get(s.frontmatter.type, 0) + 1
        by_status[s.frontmatter.status] = by_status.get(s.frontmatter.status, 0) + 1
    data = {
        "generated": str(__import__("datetime").date.today()),
        "total": len(skills),
        "by_type": by_type,
        "by_status": by_status,
        "skills": [_skill_summary(s) for s in skills],
    }
    (mem_dir / "index.yaml").write_text(yaml.dump(data, default_flow_style=False))


def _skill_summary(skill) -> dict:
    fm = skill.frontmatter
    return {
        "skill_id": fm.skill_id, "type": fm.type,
        "domain_tags": fm.domain_tags, "title": skill.title,
        "status": fm.status, "reuse_count": fm.reuse_count,
    }
