"""Memory Compressor — token-aware skill compression via Haiku."""

from __future__ import annotations

import json
import os
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

from prism.config import GLOBAL_CONFIG_DIR
from prism.memory.schemas import Skill


def count_tokens(text: str) -> int:
    try:
        import tiktoken

        return len(tiktoken.get_encoding("cl100k_base").encode(text))
    except ImportError:
        return len(text) // 4


def needs_compression(skill: Skill, limit: int = 2000) -> bool:
    return count_tokens(skill.content) > limit


_COMPRESSION_PROMPT = """\
Compress the following skill while preserving its Key Insight, trigger condition, and concrete solution.
Keep the most important information only. Target: {target_tokens} tokens maximum.

Original skill:
---
{content}
---

Respond with a single JSON object:
{{
  "title": "compressed title",
  "content": "compressed markdown content preserving key insight",
  "tokens": estimated_token_count
}}
"""


@dataclass
class CompressionResult:
    success: bool
    original_tokens: int
    compressed_tokens: int
    skill: Optional[Skill] = None
    error: str = ""


def _backup_original(skill: Skill) -> Path:
    """Create a backup of the original skill before compression."""
    backup_dir = GLOBAL_CONFIG_DIR / "memory" / "episodes" / "compressed"
    backup_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_name = f"{skill.frontmatter.skill_id}_{timestamp}.md"
    backup_path = backup_dir / backup_name

    if skill.file_path and skill.file_path.exists():
        shutil.copy2(skill.file_path, backup_path)

    return backup_path


def _parse_compression_response(text: str) -> Optional[tuple[str, str, int]]:
    """Parse the LLM response and return (title, content, tokens)."""
    try:
        data = json.loads(text.strip())
        return (data.get("title", ""), data.get("content", ""), data.get("tokens", 0))
    except (json.JSONDecodeError, KeyError):
        return None


def compress(
    skill: Skill,
    target_tokens: int = 1500,
    model: str = "claude-haiku-4-5-20251001",
    dry_run: bool = False,
) -> CompressionResult:
    """Compress a skill using Haiku LLM.

    Args:
        skill: The skill to compress
        target_tokens: Target token count
        model: Model to use for compression
        dry_run: If True, only simulate the compression

    Returns:
        CompressionResult with details of the operation
    """
    original_tokens = count_tokens(skill.content)

    if not needs_compression(skill, target_tokens):
        return CompressionResult(
            success=True,
            original_tokens=original_tokens,
            compressed_tokens=original_tokens,
            skill=skill,
            error="Skill already within target token limit",
        )

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return CompressionResult(
            success=False,
            original_tokens=original_tokens,
            compressed_tokens=0,
            error="ANTHROPIC_API_KEY not set — cannot compress",
        )

    try:
        import anthropic

        client = anthropic.Anthropic(api_key=api_key)

        prompt = _COMPRESSION_PROMPT.format(
            target_tokens=target_tokens,
            content=skill.content[:5000],  # Limit input size
        )

        message = client.messages.create(
            model=model,
            max_tokens=2048,
            messages=[{"role": "user", "content": prompt}],
        )

        result = _parse_compression_response(message.content[0].text)
        if not result:
            return CompressionResult(
                success=False,
                original_tokens=original_tokens,
                compressed_tokens=0,
                error="Failed to parse compression response",
            )

        title, compressed_content, estimated_tokens = result
        compressed_tokens = count_tokens(compressed_content)

        if dry_run:
            return CompressionResult(
                success=True,
                original_tokens=original_tokens,
                compressed_tokens=compressed_tokens,
                skill=skill,
                error="",
            )

        # Backup original
        _backup_original(skill)

        # Update skill content
        skill.title = title or skill.title
        skill.content = compressed_content

        # Save back to file
        if skill.file_path:
            _save_skill_to_file(skill)

        return CompressionResult(
            success=True,
            original_tokens=original_tokens,
            compressed_tokens=compressed_tokens,
            skill=skill,
            error="",
        )

    except Exception as exc:
        return CompressionResult(
            success=False,
            original_tokens=original_tokens,
            compressed_tokens=0,
            error=f"Compression error: {exc}",
        )


def _save_skill_to_file(skill: Skill) -> None:
    """Save a skill back to its file."""
    import yaml
    from python_frontmatter import dump

    # Build frontmatter
    fm = skill.frontmatter.model_dump()

    # Create content with frontmatter
    content = f"---\n{yaml.dump(fm, default_flow_style=False)}---\n\n# {skill.title}\n\n{skill.content}"

    skill.file_path.write_text(content, encoding="utf-8")


def get_compression_candidates(store, limit: int = 2000) -> list[Skill]:
    """Get all skills that exceed the token limit."""
    candidates = []
    for skill in store.list_all():
        if needs_compression(skill, limit):
            candidates.append(skill)
    return candidates


def restore_original(skill_id: str) -> bool:
    """Restore a skill from its most recent backup.

    Args:
        skill_id: The skill ID to restore

    Returns:
        True if restored successfully
    """
    backup_dir = GLOBAL_CONFIG_DIR / "memory" / "episodes" / "compressed"
    if not backup_dir.exists():
        return False

    # Find most recent backup for this skill
    backups = sorted(
        backup_dir.glob(f"{skill_id}_*.md"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )

    if not backups:
        return False

    # Get original location from skill file path
    from prism.memory.store import SkillStore

    db_path = GLOBAL_CONFIG_DIR / "memory" / "index.db"
    with SkillStore(db_path, False) as store:
        skill = store.get(skill_id)
        if not skill or not skill.file_path:
            return False

        # Restore backup to original location
        shutil.copy2(backups[0], skill.file_path)
        return True
