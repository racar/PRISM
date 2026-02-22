from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

_PRISM_AUGMENTED_MARKER = "<!-- PRISM AUGMENTED -->"

_CURRENT_TASK_TEMPLATE = """\
# Current Task: {task_id} — {title}

> **Project:** {project}
> **Epic:** {epic}
> **Status:** In Progress
> **Generated:** {timestamp}

---

## What to Build
{description}

---

## Acceptance Criteria
{criteria}
> If a criterion is ambiguous, escalate to the Architect Agent before implementing.

---

## PRISM Context

### Relevant Skills
{skills}

### Gotchas to Watch
{gotchas}

### Architecture Decisions in Scope
{decisions}

---

## Definition of Done
- [ ] Automated tests pass in CI
- [ ] Only files in scope of this task were modified
- [ ] `output_expected` section filled below
- [ ] Task moved to Done in Flux

---

## Output (fill when complete)
```yaml
files_modified: []
tests_added: []
decisions_made: []
notes: ""
blockers_found: []
```
"""


@dataclass
class ParsedTask:
    title: str
    description: str
    criteria: list[str] = field(default_factory=list)
    epic_title: Optional[str] = None


@dataclass
class ParsedEpic:
    title: str
    description: str
    tasks: list[ParsedTask] = field(default_factory=list)


def parse_tasks_md(path: Path) -> list[ParsedEpic]:
    return _parse_epics(path.read_text())


def _parse_epics(content: str) -> list[ParsedEpic]:
    epic_re = re.compile(r"^##\s+(?:Epic:?\s*)?(.+)$", re.MULTILINE)
    parts = epic_re.split(content)
    if len(parts) < 3:
        return [ParsedEpic("Tasks", "", _parse_tasks(content))]
    epics = []
    for i in range(1, len(parts), 2):
        body = parts[i + 1] if i + 1 < len(parts) else ""
        epics.append(ParsedEpic(parts[i].strip(), _first_para(body), _parse_tasks(body, parts[i].strip())))
    return epics


def _parse_tasks(content: str, epic_title: Optional[str] = None) -> list[ParsedTask]:
    task_re = re.compile(r"^###\s+(?:Task\s+\d+:?\s*)?(.+)$", re.MULTILINE)
    parts = task_re.split(content)
    tasks = []
    for i in range(1, len(parts), 2):
        body = parts[i + 1] if i + 1 < len(parts) else ""
        tasks.append(ParsedTask(parts[i].strip(), _first_para(body), _parse_criteria(body), epic_title))
    return tasks


def _parse_criteria(content: str) -> list[str]:
    return re.findall(r"^- \[[ x]\]\s+(.+)$", content, re.MULTILINE)


def _first_para(content: str) -> str:
    for line in content.splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and not stripped.startswith("-"):
            return stripped
    return ""


def _format_criteria(criteria: list[str]) -> str:
    if not criteria:
        return "- [ ] (No criteria parsed — add manually)\n"
    return "".join(f"- [ ] {c}\n" for c in criteria)


def _format_skill_lines(results: list) -> str:
    if not results:
        return "*(no relevant skills found)*\n"
    lines = []
    for r in results:
        fm = r.skill.frontmatter
        path = r.skill.file_path or f"~/.prism/memory/{fm.subdir()}/{fm.skill_id}.md"
        lines.append(f"- **{fm.skill_id}:** {r.skill.title} → `{path}`")
    return "\n".join(lines) + "\n"


def _filter_by_type(results: list, skill_type: str) -> list:
    return [r for r in results if r.skill.frontmatter.type == skill_type]


def generate_current_task_md(task, project_dir: Path) -> Path:
    from prism.config import GLOBAL_CONFIG_DIR, load_global_config, load_project_config
    from prism.memory.store import SkillStore

    cfg = load_global_config()
    proj_cfg = load_project_config(project_dir)
    db_path = GLOBAL_CONFIG_DIR / "memory" / "index.db"
    query = f"{task.title} {task.description}"

    with SkillStore(db_path, cfg.memory.embeddings_enabled) as store:
        results = store.search(query, top_k=10)

    skills = _filter_by_type(results, "skill") + _filter_by_type(results, "pattern")
    gotchas = _filter_by_type(results, "gotcha")
    decisions = _filter_by_type(results, "decision")

    content = _CURRENT_TASK_TEMPLATE.format(
        task_id=getattr(task, "id", "TASK"),
        title=task.title,
        project=proj_cfg.name or project_dir.name,
        epic=getattr(task, "epic_id", "—") or "—",
        timestamp=datetime.now().strftime("%Y-%m-%d %H:%M"),
        description=task.description or "*(see Flux for details)*",
        criteria=_format_criteria(getattr(task, "criteria", [])),
        skills=_format_skill_lines(skills),
        gotchas=_format_skill_lines(gotchas),
        decisions=_format_skill_lines(decisions),
    )
    output = project_dir / ".prism" / "current-task.md"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(content)
    return output
