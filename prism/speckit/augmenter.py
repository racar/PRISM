from __future__ import annotations

from pathlib import Path
from typing import Optional

from prism.board.task_mapper import ParsedTask, ParsedEpic, parse_tasks_md
from prism.config import GLOBAL_CONFIG_DIR, load_global_config
from prism.memory.injector import count_tokens
from prism.memory.store import SkillStore

_MARKER = "<!-- PRISM AUGMENTED -->"
_PER_TASK_BUDGET = 500


def is_augmented(path: Path) -> bool:
    return path.exists() and _MARKER in path.read_text(encoding="utf-8")[:120]


def find_latest_tasks_md(specs_dir: Path) -> Optional[Path]:
    candidates = sorted(specs_dir.rglob("tasks.md"), key=lambda p: p.stat().st_mtime, reverse=True)
    return candidates[0] if candidates else None


def augment_tasks_md(source: Path, force: bool = False) -> Path:
    output = source.with_name("tasks.prism.md")
    if is_augmented(output) and not force:
        return output
    epics = parse_tasks_md(source)
    cfg = load_global_config()
    db_path = GLOBAL_CONFIG_DIR / "memory" / "index.db"
    with SkillStore(db_path, cfg.memory.embeddings_enabled) as store:
        context_blocks = [_context_block(task, store) for epic in epics for task in epic.tasks]
    parts = [_MARKER + "\n", source.read_text(encoding="utf-8")]
    parts += [b for b in context_blocks if b]
    output.write_text("".join(parts), encoding="utf-8")
    return output


def _context_block(task: ParsedTask, store: SkillStore) -> str:
    results = store.search(f"{task.title} {task.description}", top_k=5)
    if not results:
        return ""
    lines = [f"\n\n---\n<!-- PRISM: {task.title} -->\n### PRISM Context\n\n**Relevant Skills:**\n"]
    used = 0
    for r in results:
        fm = r.skill.frontmatter
        line = f"- **{fm.skill_id}** ({fm.type}): {r.skill.title}\n"
        used += count_tokens(line)
        if used > _PER_TASK_BUDGET:
            break
        lines.append(line)
    return "".join(lines)
