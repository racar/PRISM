from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator

SkillType = Literal["skill", "pattern", "gotcha", "decision"]
SkillStatus = Literal["active", "deprecated", "conflicted", "needs_review"]
VerifiedBy = Literal["human", "memory_agent"]
EvaluationDecision = Literal["ADD", "UPDATE", "NOOP", "DELETE"]

_SUBDIRS: dict[str, str] = {
    "skill": "skills",
    "pattern": "skills",
    "gotcha": "gotchas",
    "decision": "decisions",
}


class SkillFrontmatter(BaseModel):
    skill_id: str
    type: SkillType
    domain_tags: list[str] = Field(min_length=1)
    scope: Literal["global", "project"]
    stack_context: list[str] = Field(default_factory=list)
    created: date
    last_used: Optional[date] = None
    reuse_count: int = 0
    project_origin: str
    status: SkillStatus = "active"
    review_after: Optional[int] = None
    supersedes: Optional[str] = None
    conflict_with: list[str] = Field(default_factory=list)
    verified_by: VerifiedBy = "human"

    @field_validator("skill_id")
    @classmethod
    def validate_skill_id(cls, v: str) -> str:
        if not re.match(r"^[a-z0-9][a-z0-9-]*$", v):
            raise ValueError("skill_id must be lowercase kebab-case (e.g. my-skill)")
        return v

    def subdir(self) -> str:
        return _SUBDIRS[self.type]


@dataclass
class Skill:
    frontmatter: SkillFrontmatter
    title: str
    content: str
    file_path: Optional[Path] = None


@dataclass
class SearchResult:
    skill: Skill
    score: float
    fts_score: float = 0.0
    semantic_score: float = 0.0


@dataclass
class EvaluationResult:
    decision: EvaluationDecision
    skill_id: str = ""
    type: str = "skill"
    domain_tags: list[str] = field(default_factory=list)
    reason: str = ""
    merge_with: str = ""
