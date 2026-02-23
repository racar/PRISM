from __future__ import annotations

import os
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from prism.agents.compatibility import check_compatibility
from prism.agents.config import (
    AgentAssignment, load_agents_config, resolve_assignment,
    validate_tool_exists, validate_model_exists,
)
from prism.agents.context_generator import generate_context_file, output_file_for_tool
from prism.config import load_global_config

_TOOL_BINARY: dict[str, str] = {
    "claude_code": "claude",
    "opencode":    "opencode",
    "cursor":      "cursor",
    "gemini":      "gemini",
    "windsurf":    "windsurf",
    "copilot":     "code",
}

_LAUNCH_SUFFIX: dict[str, str] = {
    "opencode":    ".",
    "cursor":      ".",
}


@dataclass
class LaunchResult:
    role: str
    tool: str
    model: str
    context_file: str
    launch_command: str
    skill_count: int = 0
    warnings: list[str] = field(default_factory=list)


def _tool_installed(tool: str) -> bool:
    return shutil.which(_TOOL_BINARY.get(tool, tool)) is not None


def _flux_healthy() -> bool:
    try:
        from prism.board.flux_client import FluxClient
        return FluxClient().healthy()
    except Exception:
        return False


def _listener_running(project_dir: Path) -> bool:
    pid_file = project_dir / ".prism" / "listener.pid"
    if not pid_file.exists():
        return False
    try:
        os.kill(int(pid_file.read_text().strip()), 0)
        return True
    except (ProcessLookupError, ValueError, OSError):
        return False


def _run_inject(project_dir: Path) -> int:
    from prism.config import GLOBAL_CONFIG_DIR, load_project_config
    from prism.memory.injector import inject_skills
    from prism.memory.store import SkillStore
    cfg = load_global_config()
    proj = load_project_config(project_dir)
    db = GLOBAL_CONFIG_DIR / "memory" / "index.db"
    output = project_dir / ".prism" / "injected-context.md"
    with SkillStore(db, cfg.memory.embeddings_enabled) as store:
        return inject_skills(store, proj.description or proj.name, set(proj.stack), output)


def _collect_warnings(role: str, assignment: AgentAssignment, global_cfg) -> list[str]:
    warnings: list[str] = []
    if not validate_tool_exists(assignment.tool, global_cfg):
        warnings.append(f"Tool '{assignment.tool}' not found in prism.config.yaml tools section")
    if not validate_model_exists(assignment.model, global_cfg):
        warnings.append(f"Model '{assignment.model}' not found in prism.config.yaml models section")
    compat = check_compatibility(role, assignment.tool)
    warnings.extend(compat.warnings)
    if compat.suggestion:
        warnings.append(f"Consider '{compat.suggestion}' for full {role} capabilities")
    return warnings


def _resolve_with_fallback(assignment: AgentAssignment, warnings: list[str]) -> AgentAssignment:
    if _tool_installed(assignment.tool):
        return assignment
    if assignment.fallback and _tool_installed(assignment.fallback.tool):
        warnings.append(f"'{assignment.tool}' not installed — using fallback '{assignment.fallback.tool}'")
        return assignment.fallback
    warnings.append(f"Tool '{assignment.tool}' is not installed")
    return assignment


def _build_launch_command(tool: str) -> str:
    binary = _TOOL_BINARY.get(tool, tool)
    suffix = _LAUNCH_SUFFIX.get(tool, "")
    return f"{binary} {suffix}".strip()


def prepare_launch(role: str, project_dir: Path, skip_inject: bool = False) -> LaunchResult:
    global_cfg = load_global_config()
    project_cfg = load_agents_config(project_dir)
    assignment = resolve_assignment(role, project_cfg, global_cfg)
    if assignment is None:
        raise ValueError(f"No assignment found for role '{role}'. Check .prism/AGENTS.md")

    warnings = _collect_warnings(role, assignment, global_cfg)
    assignment = _resolve_with_fallback(assignment, warnings)

    if not _flux_healthy():
        warnings.append("Flux board not reachable — run: prism board setup")
    if not _listener_running(project_dir):
        warnings.append("Board listener not running — run: prism board listen --daemon")

    skill_count = _run_inject(project_dir) if not skip_inject else 0
    ctx_path = generate_context_file(assignment.tool, project_dir)
    cmd = _build_launch_command(assignment.tool)

    return LaunchResult(
        role=role, tool=assignment.tool, model=assignment.model,
        context_file=str(ctx_path.relative_to(project_dir)),
        launch_command=cmd, skill_count=skill_count, warnings=warnings,
    )
