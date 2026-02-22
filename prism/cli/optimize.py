import sys
from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from prism.cli.health import _generate_report as generate_health_report
from prism.cli.health import _print_report as print_health_report
from prism.config import GLOBAL_CONFIG_DIR, load_global_config, load_project_config
from prism.memory.auditor import audit_constitution, format_audit_report
from prism.memory.conflict import find_all_conflicts, format_conflict_report
from prism.memory.dedup import find_duplicates, format_similarity_report
from prism.memory.promoter import analyze_usage_patterns, format_promotion_report
from prism.memory.stale import find_stale_skills, format_staleness_report
from prism.memory.store import SkillStore

console = Console()


def _run_staleness_check(
    store, skills, dry_run: bool = False, auto: bool = False
) -> dict:
    """Run staleness check and optionally mark skills."""
    stale = find_stale_skills(skills)

    if stale and auto and not dry_run:
        # Mark stale skills as needs_review
        for result in stale:
            skill = store.get(result.skill_id)
            if skill and skill.frontmatter.status == "active":
                skill.frontmatter.status = "needs_review"
                store.upsert(skill)

    return {
        "checked": len(skills),
        "stale": len(stale),
        "action": "marked as needs_review"
        if (auto and stale and not dry_run)
        else "reported",
    }


def _run_compression_check(
    store, skills, dry_run: bool = False, auto: bool = False
) -> dict:
    """Check for skills needing compression."""
    from prism.memory.compressor import get_compression_candidates

    candidates = get_compression_candidates(store, limit=2000)

    compressed_count = 0
    if candidates and auto and not dry_run:
        from prism.memory.compressor import compress

        for skill in candidates[:5]:  # Limit compression in auto mode
            result = compress(skill, target_tokens=1500, dry_run=False)
            if result.success:
                compressed_count += 1
                store.upsert(result.skill)

    return {
        "candidates": len(candidates),
        "compressed": compressed_count if (auto and not dry_run) else 0,
        "action": "compressed" if (auto and compressed_count > 0) else "reported",
    }


def _run_deduplication(
    skills, threshold: float = 0.8, dry_run: bool = False, confirm: bool = False
) -> dict:
    """Find duplicate skills."""
    duplicates = find_duplicates(skills, threshold=threshold)

    return {
        "pairs": len(duplicates),
        "action": "review required" if duplicates else "none found",
    }


def _run_conflict_detection(skills, project_cfg, dry_run: bool = False) -> dict:
    """Detect conflicts between skills."""
    # Limit to avoid excessive API calls
    conflicts = find_all_conflicts(skills[:30], max_pairs=20)

    tasks_created = 0
    if conflicts and not dry_run:
        from prism.memory.conflict import create_conflict_resolution_task

        for conflict in conflicts:
            task_id = create_conflict_resolution_task(
                conflict, project_cfg.flux_project_id
            )
            if task_id:
                tasks_created += 1

    return {
        "conflicts": len(conflicts),
        "tasks_created": tasks_created,
        "action": "tasks created in Flux"
        if (conflicts and tasks_created > 0)
        else "reported",
    }


def _run_promotion_analysis(
    skills, dry_run: bool = False, confirm: bool = False
) -> dict:
    """Analyze skills for promotion opportunities."""
    candidates = analyze_usage_patterns(skills)

    return {
        "candidates": len(candidates),
        "action": "review required" if candidates else "none found",
    }


def _run_constitution_audit(project_dir, dry_run: bool = False) -> dict:
    """Audit constitution file."""
    audit = audit_constitution(project_dir, dry_run=dry_run)

    issues_count = len(audit.issues) if audit and audit.issues else 0

    return {
        "issues": issues_count,
        "file_found": audit is not None,
        "action": "review required"
        if issues_count > 0
        else ("skipped" if audit is None else "healthy"),
    }


@click.command()
@click.option("--dry-run", is_flag=True, help="Report only, no modifications")
@click.option("--auto", is_flag=True, help="Apply safe changes without confirmation")
@click.option("--confirm", is_flag=True, help="Apply all changes including merges")
@click.option("--project-dir", default=".", type=click.Path(), show_default=True)
def optimize(dry_run: bool, auto: bool, confirm: bool, project_dir: str) -> None:
    """Run memory optimizer: compress, deduplicate, detect conflicts."""
    proj_dir = Path(project_dir).resolve()

    if not (proj_dir / ".prism").exists():
        raise click.ClickException("No .prism/ found. Run: prism init or prism attach")

    global_cfg = load_global_config()
    project_cfg = load_project_config(proj_dir)

    # Initialize store
    db_path = GLOBAL_CONFIG_DIR / "memory" / "index.db"
    skills = []

    if db_path.exists():
        with SkillStore(db_path, global_cfg.memory.embeddings_enabled) as store:
            skills = store.list_all()

            console.print(
                Panel.fit(
                    "[bold cyan]PRISM Memory Optimizer[/bold cyan]",
                    title="Fase 4",
                    border_style="cyan",
                )
            )

            if dry_run:
                console.print(
                    "[yellow]Mode: DRY-RUN (no changes will be made)[/yellow]\n"
                )
            elif auto:
                console.print("[green]Mode: AUTO (safe changes applied)[/green]\n")
            elif confirm:
                console.print("[red]Mode: CONFIRM (all changes applied)[/red]\n")
            else:
                console.print(
                    "[blue]Mode: INTERACTIVE (will prompt for actions)[/blue]\n"
                )

            # 1. Health Check (always runs)
            console.print("[bold]1. Health Check[/bold]")
            health_report = generate_health_report(proj_dir)
            exit_code = print_health_report(health_report)
            console.print()

            # 2. Staleness Check
            console.print("[bold]2. Staleness Check[/bold]")
            stale_result = _run_staleness_check(store, skills, dry_run, auto)
            console.print(
                f"   Checked {stale_result['checked']} skills, {stale_result['stale']} stale — {stale_result['action']}"
            )
            if stale_result["stale"] > 0:
                stale = find_stale_skills(skills)
                console.print(format_staleness_report(stale))
            console.print()

            # 3. Compression Check
            console.print("[bold]3. Compression Check[/bold]")
            compression_result = _run_compression_check(store, skills, dry_run, auto)
            console.print(
                f"   {compression_result['candidates']} candidates — {compression_result['action']}"
            )
            if compression_result["compressed"] > 0:
                console.print(
                    f"   [green]Compressed {compression_result['compressed']} skills[/green]"
                )
            console.print()

            # 4. Deduplication (report only unless confirm)
            console.print("[bold]4. Deduplication Check (TF-IDF)[/bold]")
            dedup_result = _run_deduplication(
                skills, dry_run=dry_run or not confirm, confirm=confirm
            )
            console.print(
                f"   {dedup_result['pairs']} similar pairs — {dedup_result['action']}"
            )
            if dedup_result["pairs"] > 0:
                duplicates = find_duplicates(skills)
                console.print(format_similarity_report(duplicates))
            console.print()

            # 5. Conflict Detection
            console.print("[bold]5. Conflict Detection (Haiku)[/bold]")
            conflict_result = _run_conflict_detection(skills, project_cfg, dry_run)
            console.print(
                f"   {conflict_result['conflicts']} conflicts — {conflict_result['action']}"
            )
            if conflict_result["conflicts"] > 0:
                from prism.memory.conflict import find_all_conflicts

                conflicts = find_all_conflicts(skills[:30])
                console.print(format_conflict_report(conflicts))
            console.print()

            # 6. Pattern Promotion
            console.print("[bold]6. Pattern Promotion[/bold]")
            promo_result = _run_promotion_analysis(skills, dry_run, confirm)
            console.print(
                f"   {promo_result['candidates']} candidates — {promo_result['action']}"
            )
            if promo_result["candidates"] > 0:
                candidates = analyze_usage_patterns(skills)
                console.print(format_promotion_report(candidates))
            console.print()

            # 7. Constitution Audit
            console.print("[bold]7. Constitution Audit[/bold]")
            const_result = _run_constitution_audit(proj_dir, dry_run)
            if const_result["file_found"]:
                console.print(
                    f"   {const_result['issues']} issues — {const_result['action']}"
                )
                if const_result["issues"] > 0:
                    audit = audit_constitution(proj_dir, dry_run=True)
                    console.print(format_audit_report(audit))
            else:
                console.print("   [dim]No constitution.md found (skipped)[/dim]")
            console.print()

            # Summary
            console.print(
                Panel.fit(
                    f"[bold]Optimization Summary[/bold]\n\n"
                    f"Health: {'✅' if exit_code == 0 else '⚠️' if exit_code == 1 else '❌'}\n"
                    f"Stale skills: {stale_result['stale']}\n"
                    f"Compression candidates: {compression_result['candidates']}\n"
                    f"Duplicate pairs: {dedup_result['pairs']}\n"
                    f"Conflicts: {conflict_result['conflicts']}\n"
                    f"Promotions: {promo_result['candidates']}\n"
                    f"Constitution issues: {const_result['issues']}",
                    border_style="green"
                    if all(
                        [
                            exit_code == 0,
                            stale_result["stale"] == 0,
                            compression_result["candidates"] == 0,
                            dedup_result["pairs"] == 0,
                            conflict_result["conflicts"] == 0,
                        ]
                    )
                    else "yellow",
                )
            )
    else:
        console.print(
            "[yellow]Warning: Memory store not found — some checks skipped[/yellow]"
        )
