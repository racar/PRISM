from __future__ import annotations

from dataclasses import dataclass, field

_ROLE_CAPABILITIES: dict[str, set[str]] = {
    "architect":  {"file_read_write", "spec_kit_commands", "flux_mcp"},
    "developer":  {"file_read_write", "bash_execution", "flux_mcp"},
    "reviewer":   {"file_read_write", "flux_mcp"},
    "memory":     {"file_read_write"},
    "optimizer":  {"file_read_write"},
}

_TOOL_CAPABILITIES: dict[str, set[str]] = {
    "claude_code": {"file_read_write", "bash_execution", "flux_mcp", "spec_kit_commands"},
    "opencode":    {"file_read_write", "bash_execution", "flux_mcp"},
    "cursor":      {"file_read_write", "bash_execution"},
    "gemini":      {"file_read_write", "bash_execution"},
    "windsurf":    {"file_read_write", "bash_execution"},
    "copilot":     {"file_read_write"},
}

_BEST_TOOL_FOR_ROLE: dict[str, str] = {
    "architect": "claude_code",
    "developer": "opencode",
    "reviewer":  "claude_code",
    "memory":    "claude_code",
    "optimizer": "claude_code",
}


@dataclass
class CompatibilityResult:
    compatible: bool
    missing: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    suggestion: str = ""


def check_compatibility(role: str, tool: str) -> CompatibilityResult:
    required = _ROLE_CAPABILITIES.get(role, set())
    available = _TOOL_CAPABILITIES.get(tool, set())
    missing = sorted(required - available)
    warnings = [f"'{cap}' not supported by '{tool}'" for cap in missing]
    suggestion = _BEST_TOOL_FOR_ROLE.get(role, "") if missing else ""
    return CompatibilityResult(
        compatible=len(missing) == 0,
        missing=missing,
        warnings=warnings,
        suggestion=suggestion,
    )


def known_tools() -> list[str]:
    return list(_TOOL_CAPABILITIES.keys())
