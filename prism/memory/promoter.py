"""Pattern Promoter — promote frequently-used gotchas to patterns."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from prism.config import GLOBAL_CONFIG_DIR
from prism.memory.schemas import Skill


@dataclass
class PromotionCandidate:
    skill_id: str
    current_type: str
    proposed_type: str
    usage_count: int
    project_count: int
    reason: str


def analyze_usage_patterns(
    skills: list[Skill], min_project_count: int = 3
) -> list[PromotionCandidate]:
    """Analyze skills to find promotion candidates.

    Detects:
    1. Gotchas used across multiple projects → promote to Pattern
    2. Project-scoped skills used everywhere → promote to Global scope

    Args:
        skills: List of skills to analyze
        min_project_count: Minimum number of projects to consider for promotion

    Returns:
        List of promotion candidates
    """
    candidates = []

    # Group by project_origin to count project usage
    project_usage = defaultdict(set)  # skill_id -> set of projects
    skill_by_id = {}

    for skill in skills:
        sid = skill.frontmatter.skill_id
        project_usage[sid].add(skill.frontmatter.project_origin)
        skill_by_id[sid] = skill

    # Analyze each skill
    for skill in skills:
        sid = skill.frontmatter.skill_id
        projects = project_usage[sid]
        project_count = len(projects)

        # Check 1: Gotcha -> Pattern promotion
        if skill.frontmatter.type == "gotcha" and project_count >= min_project_count:
            candidates.append(
                PromotionCandidate(
                    skill_id=sid,
                    current_type="gotcha",
                    proposed_type="pattern",
                    usage_count=skill.frontmatter.reuse_count,
                    project_count=project_count,
                    reason=f"Used across {project_count} projects — consider elevating to reusable pattern",
                )
            )

        # Check 2: Project -> Global scope promotion
        if skill.frontmatter.scope == "project":
            # Count total unique projects in memory
            all_projects = set()
            for s in skills:
                all_projects.add(s.frontmatter.project_origin)

            total_projects = len(all_projects)
            if total_projects > 0 and project_count >= total_projects:
                candidates.append(
                    PromotionCandidate(
                        skill_id=sid,
                        current_type=skill.frontmatter.type,
                        proposed_type=skill.frontmatter.type,  # Same type, just scope change
                        usage_count=skill.frontmatter.reuse_count,
                        project_count=project_count,
                        reason=f"Used in all {project_count} known projects — consider global scope",
                    )
                )

    # Sort by project count (most universal first)
    candidates.sort(key=lambda x: x.project_count, reverse=True)

    return candidates


def apply_promotion(
    skill_id: str,
    new_type: Optional[str] = None,
    new_scope: Optional[str] = None,
    store=None,
    dry_run: bool = False,
) -> bool:
    """Apply a promotion to a skill.

    Args:
        skill_id: ID of skill to promote
        new_type: New type to set (if type promotion)
        new_scope: New scope to set (if scope promotion)
        store: SkillStore instance
        dry_run: If True, only simulate

    Returns:
        True if successful
    """
    if dry_run or store is None:
        return True

    skill = store.get(skill_id)
    if not skill:
        return False

    if new_type:
        skill.frontmatter.type = new_type  # type: ignore

    if new_scope:
        skill.frontmatter.scope = new_scope  # type: ignore

    store.upsert(skill)
    return True


def format_promotion_report(candidates: list[PromotionCandidate]) -> str:
    """Format promotion candidates for human-readable output."""
    if not candidates:
        return "✅ No promotion candidates detected."

    lines = [f"📈 {len(candidates)} promotion candidate(s) found:", ""]

    for i, candidate in enumerate(candidates, 1):
        lines.append(f"{i}. `{candidate.skill_id}`")
        if candidate.current_type != candidate.proposed_type:
            lines.append(
                f"   Type: {candidate.current_type} → {candidate.proposed_type}"
            )
        lines.append(
            f"   Usage: {candidate.usage_count} times across {candidate.project_count} projects"
        )
        lines.append(f"   💡 {candidate.reason}")
        lines.append("")

    return "\n".join(lines)
