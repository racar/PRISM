"""Conflict Detector — LLM-based contradiction detection between skills."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Optional

from prism.memory.schemas import Skill


@dataclass
class ConflictResult:
    skill_a: str
    skill_b: str
    conflict_detected: bool
    conflict_type: str  # "direct", "approach", "recommendation"
    description: str
    resolution_hint: str


_CONFLICT_PROMPT = """\
You are analyzing two software development skills to detect if they contain contradictory or incompatible instructions.

Skill A:
---
Title: {title_a}
Content: {content_a}
---

Skill B:
---
Title: {title_b}  
Content: {content_b}
---

Domain overlap: {domains}

Analyze if these skills contradict each other or recommend incompatible approaches for the same scenario. Consider:
1. Direct contradictions (one says "do X", other says "never do X")
2. Approach conflicts (different incompatible methodologies)
3. Recommendation conflicts (solutions that cannot coexist)

Respond with a single JSON object:
{{
  "conflict_detected": true|false,
  "conflict_type": "none|direct|approach|recommendation",
  "description": "explanation of the conflict if detected",
  "resolution_hint": "suggested way to resolve or clarify"
}}
"""


def _build_conflict_prompt(skill_a: Skill, skill_b: Skill) -> str:
    """Build the prompt for conflict detection."""
    domains_a = set(skill_a.frontmatter.domain_tags)
    domains_b = set(skill_b.frontmatter.domain_tags)
    overlap = domains_a & domains_b

    domain_str = ", ".join(overlap) if overlap else "none (different domains)"

    return _CONFLICT_PROMPT.format(
        title_a=skill_a.title,
        content_a=skill_a.content[:2000],
        title_b=skill_b.title,
        content_b=skill_b.content[:2000],
        domains=domain_str,
    )


def _parse_conflict_response(text: str) -> Optional[ConflictResult]:
    """Parse the LLM response."""
    try:
        data = json.loads(text.strip())
        return ConflictResult(
            skill_a="",  # Will be filled by caller
            skill_b="",  # Will be filled by caller
            conflict_detected=data.get("conflict_detected", False),
            conflict_type=data.get("conflict_type", "none"),
            description=data.get("description", ""),
            resolution_hint=data.get("resolution_hint", ""),
        )
    except json.JSONDecodeError:
        return None


def detect_conflict(
    skill_a: Skill,
    skill_b: Skill,
    model: str = "claude-haiku-4-5-20251001",
    dry_run: bool = False,
) -> Optional[ConflictResult]:
    """Detect if two skills contradict each other using Haiku.

    Args:
        skill_a: First skill to compare
        skill_b: Second skill to compare
        model: Model to use for detection
        dry_run: If True, simulate without API call

    Returns:
        ConflictResult if conflict detected, None otherwise or on error
    """
    # Skip if no domain overlap
    domains_a = set(skill_a.frontmatter.domain_tags)
    domains_b = set(skill_b.frontmatter.domain_tags)
    if not domains_a & domains_b:
        return None

    # Skip if same skill
    if skill_a.frontmatter.skill_id == skill_b.frontmatter.skill_id:
        return None

    # Skip if either is already marked as conflicted
    if (
        skill_a.frontmatter.status == "conflicted"
        or skill_b.frontmatter.status == "conflicted"
    ):
        return None

    if dry_run:
        # Return a simulated result for testing
        return ConflictResult(
            skill_a=skill_a.frontmatter.skill_id,
            skill_b=skill_b.frontmatter.skill_id,
            conflict_detected=True,
            conflict_type="approach",
            description="Simulated conflict for dry-run mode",
            resolution_hint="Review both skills manually",
        )

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return None

    try:
        import anthropic

        client = anthropic.Anthropic(api_key=api_key)

        prompt = _build_conflict_prompt(skill_a, skill_b)

        message = client.messages.create(
            model=model,
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )

        result = _parse_conflict_response(message.content[0].text)
        if result and result.conflict_detected:
            result.skill_a = skill_a.frontmatter.skill_id
            result.skill_b = skill_b.frontmatter.skill_id
            return result

        return None

    except Exception:
        return None


def find_all_conflicts(
    skills: list[Skill], model: str = "claude-haiku-4-5-20251001", max_pairs: int = 50
) -> list[ConflictResult]:
    """Find all conflicting skill pairs in a list.

    Args:
        skills: List of skills to check
        model: Model to use for detection
        max_pairs: Maximum number of pairs to check (to limit API calls)

    Returns:
        List of detected conflicts
    """
    conflicts = []
    checked = 0

    # Prioritize checking skills in the same domain
    domain_groups = {}
    for skill in skills:
        for domain in skill.frontmatter.domain_tags:
            if domain not in domain_groups:
                domain_groups[domain] = []
            domain_groups[domain].append(skill)

    # Check within each domain group
    for domain, group in domain_groups.items():
        n = len(group)
        for i in range(n):
            for j in range(i + 1, n):
                if checked >= max_pairs:
                    break

                result = detect_conflict(group[i], group[j], model)
                checked += 1

                if result and result.conflict_detected:
                    conflicts.append(result)

    return conflicts


def create_conflict_resolution_task(
    conflict: ConflictResult, flux_project_id: str
) -> Optional[str]:
    """Create a Flux task for resolving a conflict.

    Args:
        conflict: The conflict to resolve
        flux_project_id: Project ID in Flux

    Returns:
        Task ID if created successfully
    """
    try:
        from prism.board.flux_client import FluxClient

        client = FluxClient()

        title = f"DECISION: Resolve conflict between {conflict.skill_a} and {conflict.skill_b}"

        body = f"""# Skill Conflict Detected

**Type:** {conflict.conflict_type}

**Skills involved:**
- `{conflict.skill_a}`
- `{conflict.skill_b}`

**Description:**
{conflict.description}

**Suggested resolution:**
{conflict.resolution_hint}

---

**Action required:**
1. Review both skills in `~/.prism/memory/`
2. Decide which approach to keep or how to reconcile
3. Update skill status and mark as resolved
"""

        task = client.create_task(
            project_id=flux_project_id, title=title, body=body, epic_id=None
        )

        return task.id if hasattr(task, "id") else None

    except Exception:
        return None


def format_conflict_report(conflicts: list[ConflictResult]) -> str:
    """Format conflicts for human-readable output."""
    if not conflicts:
        return "No conflicting skills detected."

    lines = [f"⚠️  {len(conflicts)} conflict(s) detected:", ""]

    for i, conflict in enumerate(conflicts, 1):
        lines.append(f"{i}. `{conflict.skill_a}` vs `{conflict.skill_b}`")
        lines.append(f"   Type: {conflict.conflict_type}")
        lines.append(f"   {conflict.description}")
        lines.append(f"   💡 {conflict.resolution_hint}")
        lines.append("")

    return "\n".join(lines)
