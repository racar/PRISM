"""Constitution Auditor — analyze and maintain constitution.md files."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class ConstitutionIssue:
    issue_type: str  # "contradiction", "redundancy", "obsolete"
    description: str
    principle_a: Optional[str]
    principle_b: Optional[str]
    suggestion: str


@dataclass
class ConstitutionAudit:
    issues: list[ConstitutionIssue]
    consolidation_proposal: Optional[str]


_AUDIT_PROMPT = """\
You are analyzing a software development constitution document that contains guiding principles.

Constitution:
---
{content}
---

Analyze for:
1. Contradictions: Principles that conflict with each other
2. Redundancies: Principles that say the same thing in different ways
3. Obsolete: Principles that may no longer apply

Respond with a single JSON object:
{{
  "issues": [
    {{
      "issue_type": "contradiction|redundancy|obsolete",
      "description": "explanation",
      "principle_a": "relevant principle text or id",
      "principle_b": "relevant principle text or id (for contradictions)",
      "suggestion": "how to resolve"
    }}
  ],
  "consolidation_proposal": "optional proposed rewrite if issues found"
}}
"""


def _find_constitution(project_dir: Path) -> Optional[Path]:
    """Find constitution.md in expected locations.

    Priority:
    1. .prism/constitution.md (PRISM native)
    2. .specify/memory/constitution.md (Spec-Kit compatibility)

    Returns:
        Path to constitution if found, None otherwise
    """
    # Check PRISM native location
    prism_constitution = project_dir / ".prism" / "constitution.md"
    if prism_constitution.exists():
        return prism_constitution

    # Check Spec-Kit location
    specify_constitution = project_dir / ".specify" / "memory" / "constitution.md"
    if specify_constitution.exists():
        return specify_constitution

    return None


def _parse_audit_response(text: str) -> ConstitutionAudit:
    """Parse the LLM audit response."""
    try:
        data = json.loads(text.strip())
        issues = []

        for issue_data in data.get("issues", []):
            issues.append(
                ConstitutionIssue(
                    issue_type=issue_data.get("issue_type", "unknown"),
                    description=issue_data.get("description", ""),
                    principle_a=issue_data.get("principle_a"),
                    principle_b=issue_data.get("principle_b"),
                    suggestion=issue_data.get("suggestion", ""),
                )
            )

        return ConstitutionAudit(
            issues=issues, consolidation_proposal=data.get("consolidation_proposal")
        )
    except json.JSONDecodeError:
        return ConstitutionAudit(issues=[], consolidation_proposal=None)


def audit_constitution(
    project_dir: Path, model: str = "claude-haiku-4-5-20251001", dry_run: bool = False
) -> Optional[ConstitutionAudit]:
    """Audit the project's constitution for issues.

    Args:
        project_dir: Project directory to audit
        model: Model to use for auditing
        dry_run: If True, simulate without API call

    Returns:
        ConstitutionAudit if constitution exists and audit successful
    """
    constitution_path = _find_constitution(project_dir)

    if not constitution_path:
        # No constitution found — skip silently as per DT-7
        return None

    content = constitution_path.read_text(encoding="utf-8")

    if dry_run:
        # Return simulated result
        return ConstitutionAudit(
            issues=[
                ConstitutionIssue(
                    issue_type="contradiction",
                    description="Simulated issue for dry-run",
                    principle_a="Principle A",
                    principle_b="Principle B",
                    suggestion="Review both principles",
                )
            ],
            consolidation_proposal=None,
        )

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return None

    try:
        import anthropic

        client = anthropic.Anthropic(api_key=api_key)

        prompt = _AUDIT_PROMPT.format(content=content[:5000])

        message = client.messages.create(
            model=model,
            max_tokens=2048,
            messages=[{"role": "user", "content": prompt}],
        )

        return _parse_audit_response(message.content[0].text)

    except Exception:
        return None


def format_audit_report(audit: Optional[ConstitutionAudit]) -> str:
    """Format constitution audit for human-readable output."""
    if audit is None:
        return "ℹ️  No constitution.md found (skipping audit)"

    if not audit.issues:
        return "✅ Constitution looks healthy — no issues detected."

    lines = [f"📜 Constitution Issues: {len(audit.issues)} found", ""]

    for i, issue in enumerate(audit.issues, 1):
        lines.append(f"{i}. [{issue.issue_type.upper()}] {issue.description}")
        if issue.principle_a:
            lines.append(f"   A: {issue.principle_a[:60]}...")
        if issue.principle_b:
            lines.append(f"   B: {issue.principle_b[:60]}...")
        lines.append(f"   💡 {issue.suggestion}")
        lines.append("")

    if audit.consolidation_proposal:
        lines.append("📝 Consolidation proposal available (review with --confirm)")

    return "\n".join(lines)
