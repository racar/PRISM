"""Staleness Checker — detect skills that haven't been used recently."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Optional

from prism.memory.schemas import Skill, SkillStatus


@dataclass
class StalenessResult:
    skill_id: str
    last_used: Optional[date]
    days_since: int
    review_after: Optional[int]
    is_stale: bool
    reason: str


def _parse_date(date_value) -> Optional[date]:
    """Parse a date from various formats."""
    if date_value is None:
        return None

    if isinstance(date_value, date):
        return date_value

    try:
        return datetime.strptime(str(date_value), "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


def check_staleness(skill: Skill, default_review_after: int = 90) -> StalenessResult:
    """Check if a skill has become stale (not used recently).

    Args:
        skill: The skill to check
        default_review_after: Default days before marking stale if not specified

    Returns:
        StalenessResult with staleness details
    """
    skill_id = skill.frontmatter.skill_id
    last_used = _parse_date(skill.frontmatter.last_used)
    review_after = skill.frontmatter.review_after or default_review_after

    today = date.today()

    if last_used is None:
        # Never used - check creation date
        created = _parse_date(skill.frontmatter.created)
        if created:
            days_since = (today - created).days
        else:
            days_since = 0

        is_stale = days_since > review_after
        reason = (
            f"Never used since creation ({days_since} days ago)" if is_stale else ""
        )
    else:
        days_since = (today - last_used).days
        is_stale = days_since > review_after
        reason = (
            f"Last used {days_since} days ago (limit: {review_after})"
            if is_stale
            else ""
        )

    return StalenessResult(
        skill_id=skill_id,
        last_used=last_used,
        days_since=days_since,
        review_after=review_after,
        is_stale=is_stale,
        reason=reason,
    )


def find_stale_skills(
    skills: list[Skill], default_review_after: int = 90
) -> list[StalenessResult]:
    """Find all stale skills in a list.

    Args:
        skills: List of skills to check
        default_review_after: Default days before marking stale

    Returns:
        List of stale skills (only those that are actually stale)
    """
    results = []
    for skill in skills:
        if skill.frontmatter.status == "deprecated":
            continue  # Skip already deprecated skills

        result = check_staleness(skill, default_review_after)
        if result.is_stale:
            results.append(result)

    # Sort by days since last use (most stale first)
    results.sort(key=lambda x: x.days_since, reverse=True)

    return results


def mark_stale_skills(
    skills: list[Skill], store, default_review_after: int = 90, dry_run: bool = False
) -> list[StalenessResult]:
    """Find and optionally mark stale skills as NEEDS_REVIEW.

    Args:
        skills: List of skills to check
        store: SkillStore instance
        default_review_after: Default days before marking stale
        dry_run: If True, only report without updating

    Returns:
        List of stale skills
    """
    stale = find_stale_skills(skills, default_review_after)

    if not dry_run:
        for result in stale:
            skill = store.get(result.skill_id)
            if skill and skill.frontmatter.status == "active":
                skill.frontmatter.status = "needs_review"  # type: ignore
                store.upsert(skill)

    return stale


def format_staleness_report(results: list[StalenessResult]) -> str:
    """Format staleness results for human-readable output."""
    if not results:
        return "✅ No stale skills detected."

    lines = [f"⚠️  {len(results)} skill(s) need review (stale):", ""]

    for result in results:
        last_used_str = result.last_used.isoformat() if result.last_used else "never"
        lines.append(f"• `{result.skill_id}` — {result.days_since} days since use")
        lines.append(
            f"  Last used: {last_used_str} (limit: {result.review_after} days)"
        )
        lines.append("")

    return "\n".join(lines)
