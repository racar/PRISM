"""Memory Compressor — token-aware skill compression via Haiku. Implemented in Fase 4."""
from __future__ import annotations

from pathlib import Path

from prism.memory.schemas import Skill


def count_tokens(text: str) -> int:
    try:
        import tiktoken
        return len(tiktoken.get_encoding("cl100k_base").encode(text))
    except ImportError:
        return len(text) // 4


def needs_compression(skill: Skill, limit: int = 2000) -> bool:
    return count_tokens(skill.content) > limit


def compress(skill: Skill, target_tokens: int = 1500, model: str = "claude-haiku-4-5-20251001") -> Skill:
    raise NotImplementedError("Compression is implemented in Fase 4")
