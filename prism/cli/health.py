from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.table import Table

from prism.config import GLOBAL_CONFIG_DIR, load_global_config, load_project_config
from prism.memory.compressor import count_tokens
from prism.memory.store import SkillStore

console = Console()


@dataclass
class FileHealth:
    path: Path
    tokens: int
    limit: int
    status: str  # "ok", "warning", "critical"


@dataclass
class SkillHealth:
    skill_id: str
    status: str
    last_used: Optional[str] = None
    days_since_used: Optional[int] = None


@dataclass
class HealthReport:
    project_name: str
    files: list[FileHealth] = field(default_factory=list)
    skills: list[SkillHealth] = field(default_factory=list)
    total_budget_used: int = 0
    total_budget_limit: int = 0


def _check_file(path: Path, limit: int) -> FileHealth:
    """Check a single file against its token limit."""
    if not path.exists():
        return FileHealth(path=path, tokens=0, limit=limit, status="ok")

    content = path.read_text(encoding="utf-8")
    tokens = count_tokens(content)

    percentage = (tokens / limit) * 100 if limit > 0 else 0

    if percentage > 100:
        status = "critical"
    elif percentage > 90:
        status = "warning"
    else:
        status = "ok"

    return FileHealth(path=path, tokens=tokens, limit=limit, status=status)


def _check_skills(store: SkillStore) -> list[SkillHealth]:
    """Check all skills in the store."""
    from datetime import date, datetime

    skills = store.list_all()
    health_list = []

    for skill in skills:
        days_since = None
        last_used_str = None

        if skill.frontmatter.last_used:
            try:
                last_used = skill.frontmatter.last_used
                # Handle both date objects and string representations
                if isinstance(last_used, date):
                    last_used_date = last_used
                    last_used_str = last_used.isoformat()
                else:
                    last_used_date = datetime.strptime(
                        str(last_used), "%Y-%m-%d"
                    ).date()
                    last_used_str = str(last_used)

                days_since = (date.today() - last_used_date).days
            except (ValueError, TypeError):
                pass

        health_list.append(
            SkillHealth(
                skill_id=skill.frontmatter.skill_id,
                status=skill.frontmatter.status,
                last_used=last_used_str,
                days_since_used=days_since,
            )
        )

    return health_list


def _generate_report(project_dir: Path) -> HealthReport:
    """Generate a complete health report."""
    global_cfg = load_global_config()
    project_cfg = load_project_config(project_dir)
    limits = global_cfg.memory.context_limits

    report = HealthReport(
        project_name=project_cfg.name or project_dir.name,
        total_budget_limit=limits.total_budget,
    )

    # Check project context files
    prism_md = project_dir / ".prism" / "PRISM.md"
    injected = project_dir / ".prism" / "injected-context.md"

    report.files.append(_check_file(prism_md, limits.prism_md))
    report.files.append(_check_file(injected, limits.injected_context))

    # Check skills
    db_path = GLOBAL_CONFIG_DIR / "memory" / "index.db"
    if db_path.exists():
        with SkillStore(db_path, global_cfg.memory.embeddings_enabled) as store:
            report.skills = _check_skills(store)

            # Check individual skill files
            for skill in store.list_all():
                if skill.file_path and skill.file_path.exists():
                    type_limit = getattr(limits, skill.frontmatter.type, limits.skill)
                    report.files.append(_check_file(skill.file_path, type_limit))

    # Calculate total budget
    report.total_budget_used = sum(f.tokens for f in report.files)

    return report


def _print_report(report: HealthReport) -> int:
    """Print the health report and return exit code."""
    console.print(f"\n[bold]PRISM Health Report[/bold] — {report.project_name}")
    console.print("─" * 50)

    has_warnings = False
    has_critical = False

    # Print file health
    for file_health in report.files:
        icon = (
            "✅"
            if file_health.status == "ok"
            else "⚠️"
            if file_health.status == "warning"
            else "❌"
        )
        color = (
            "green"
            if file_health.status == "ok"
            else "yellow"
            if file_health.status == "warning"
            else "red"
        )

        rel_path = (
            file_health.path.relative_to(Path.cwd())
            if str(file_health.path).startswith(str(Path.cwd()))
            else file_health.path
        )
        percentage = (
            (file_health.tokens / file_health.limit) * 100
            if file_health.limit > 0
            else 0
        )

        console.print(
            f"{icon} [{color}]{rel_path}[/{color}]: {file_health.tokens:,} tokens (limit: {file_health.limit:,}) — {percentage:.0f}%"
        )

        if file_health.status == "warning":
            has_warnings = True
        elif file_health.status == "critical":
            has_critical = True

    # Print skill status summary
    if report.skills:
        console.print("\n[bold]Skill Status:[/bold]")
        status_counts = {}
        for skill in report.skills:
            status_counts[skill.status] = status_counts.get(skill.status, 0) + 1

        for status, count in status_counts.items():
            color = (
                "green"
                if status == "active"
                else "yellow"
                if status == "needs_review"
                else "red"
            )
            console.print(f"  [{color}]{count} skills {status.upper()}[/{color}]")

        # Show skills needing attention
        attention_skills = [s for s in report.skills if s.status != "active"]
        if attention_skills:
            has_warnings = True
            console.print("\n[yellow]Skills needing attention:[/yellow]")
            for skill in attention_skills:
                days_info = (
                    f" (last used: {skill.days_since_used} days ago)"
                    if skill.days_since_used
                    else ""
                )
                console.print(f"  - {skill.skill_id}: {skill.status}{days_info}")

    # Print budget summary
    percentage = (
        (report.total_budget_used / report.total_budget_limit) * 100
        if report.total_budget_limit > 0
        else 0
    )
    color = "green" if percentage < 70 else "yellow" if percentage < 90 else "red"
    console.print(
        f"\n[bold]Budget:[/bold] [{color}]{report.total_budget_used:,} / {report.total_budget_limit:,} tokens ({percentage:.0f}%)[/{color}]"
    )

    # Overall status
    if has_critical:
        console.print("\n[red bold]Status: CRITICAL — Action required[/red bold]")
        return 2
    elif has_warnings:
        console.print(
            "\n[yellow bold]Status: WARNINGS — Review recommended[/yellow bold]"
        )
        return 1
    else:
        console.print("\n[green bold]Status: HEALTHY[/green bold]")
        return 0


@click.command()
@click.option("--project-dir", default=".", type=click.Path(), show_default=True)
def health(project_dir: str) -> None:
    """Check token budgets and skill health across the project."""
    proj_dir = Path(project_dir).resolve()

    if not (proj_dir / ".prism").exists():
        raise click.ClickException("No .prism/ found. Run: prism init or prism attach")

    report = _generate_report(proj_dir)
    exit_code = _print_report(report)
    sys.exit(exit_code)
