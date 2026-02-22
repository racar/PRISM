from __future__ import annotations

import json
import os
from typing import Optional

from prism.memory.schemas import EvaluationDecision, EvaluationResult

_EVAL_PROMPT = """\
You are a memory agent for a software development system.
Evaluate whether the following content should be saved as a reusable skill.

Criteria for ADD (all should hold):
1. Genuine discovery: not just following standard documentation
2. Transferable: useful in another project 6 months from now
3. Verified: tested or confirmed to work
4. Clear trigger: specific situation when this applies

Content to evaluate:
---
{content}
---

Existing skills in same domain (for duplicate detection):
{existing}

Respond with a single JSON object only — no markdown, no explanation:
{{
  "decision": "ADD|UPDATE|NOOP|DELETE",
  "skill_id": "suggested-kebab-id",
  "type": "skill|pattern|gotcha|decision",
  "domain_tags": ["tag1", "tag2"],
  "reason": "one sentence explanation",
  "merge_with": "existing-skill-id-or-empty"
}}
"""


def _build_prompt(content: str, existing_ids: list[str]) -> str:
    existing = "\n".join(f"- {sid}" for sid in existing_ids) or "(none)"
    return _EVAL_PROMPT.format(content=content[:3000], existing=existing)


def _parse_response(text: str) -> EvaluationResult:
    try:
        data = json.loads(text.strip())
        return EvaluationResult(
            decision=data.get("decision", "NOOP"),
            skill_id=data.get("skill_id", ""),
            type=data.get("type", "skill"),
            domain_tags=data.get("domain_tags", []),
            reason=data.get("reason", ""),
            merge_with=data.get("merge_with", ""),
        )
    except (json.JSONDecodeError, KeyError):
        return EvaluationResult(decision="NOOP", reason="Failed to parse evaluator response")


def _fallback_result(reason: str) -> EvaluationResult:
    return EvaluationResult(decision="NOOP", reason=reason)


def evaluate(content: str, existing_ids: Optional[list[str]] = None, model: str = "claude-haiku-4-5-20251001") -> EvaluationResult:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return _fallback_result("ANTHROPIC_API_KEY not set — skipping LLM evaluation")
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        message = client.messages.create(
            model=model,
            max_tokens=512,
            messages=[{"role": "user", "content": _build_prompt(content, existing_ids or [])}],
        )
        return _parse_response(message.content[0].text)
    except Exception as exc:
        return _fallback_result(f"Evaluator error: {exc}")
