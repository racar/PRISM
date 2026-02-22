from __future__ import annotations

from datetime import date
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from prism.agents.compatibility import CompatibilityResult, check_compatibility
from prism.agents.config import (
    AgentAssignment, ProjectAgentsConfig,
    load_agents_config, resolve_assignment,
    validate_model_exists, validate_tool_exists,
)
from prism.agents.context_generator import (
    generate_context_file, is_manually_edited, output_file_for_tool,
)
from prism.config import AgentRoleAssignment, AgentRoleDefault, PrismConfig


# ── Fixtures ──────────────────────────────────────────────────────────────────

def _global_cfg(**extra_tools) -> PrismConfig:
    from prism.config import ToolConfig
    tools = {
        "claude_code": ToolConfig(command="claude", context_file="CLAUDE.md", mcp_support=True),
        "opencode": ToolConfig(command="opencode", context_file="AGENTS.md", mcp_support=True),
    }
    tools.update(extra_tools)
    return PrismConfig(
        tools=tools,
        models={
            "anthropic": {"opus": "claude-opus-4-6", "sonnet": "claude-sonnet-4-6", "haiku": "claude-haiku-4-5"},
            "moonshot": {"kimi": "kimi-k2"},
        },
        agent_roles={
            "architect": AgentRoleDefault(default=AgentRoleAssignment(tool="claude_code", model="anthropic.opus")),
            "developer": AgentRoleDefault(default=AgentRoleAssignment(tool="opencode", model="moonshot.kimi")),
        },
    )


def _agents_md_content(tool: str = "claude_code", model: str = "anthropic.opus") -> str:
    return f"""\
project: test-project
version: "1.0"
agents:
  architect:
    tool: {tool}
    model: {model}
    reason: Testing
    fallback:
      tool: opencode
      model: moonshot.kimi
  developer:
    tool: opencode
    model: moonshot.kimi
"""


@pytest.fixture
def project_dir(tmp_path) -> Path:
    prism_dir = tmp_path / ".prism"
    prism_dir.mkdir()
    (prism_dir / "PRISM.md").write_text("# Test Project\n\nProject overview.")
    (prism_dir / "AGENTS.md").write_text(_agents_md_content())
    (prism_dir / "project.yaml").write_text("name: test-project\n")
    return tmp_path


# ── 3.1 AGENTS.md parser ─────────────────────────────────────────────────────

def test_load_agents_config_parses_agents(project_dir):
    cfg = load_agents_config(project_dir)
    assert cfg.project == "test-project"
    assert "architect" in cfg.agents
    assert cfg.agents["architect"].tool == "claude_code"
    assert cfg.agents["architect"].model == "anthropic.opus"


def test_load_agents_config_parses_fallback(project_dir):
    cfg = load_agents_config(project_dir)
    fallback = cfg.agents["architect"].fallback
    assert fallback is not None
    assert fallback.tool == "opencode"


def test_load_agents_config_missing_file(tmp_path):
    (tmp_path / ".prism").mkdir()
    cfg = load_agents_config(tmp_path)
    assert cfg.agents == {}


def test_resolve_assignment_project_overrides_global(project_dir):
    project_cfg = load_agents_config(project_dir)
    global_cfg = _global_cfg()
    assignment = resolve_assignment("architect", project_cfg, global_cfg)
    assert assignment.tool == "claude_code"
    assert assignment.model == "anthropic.opus"


def test_resolve_assignment_falls_back_to_global(tmp_path):
    (tmp_path / ".prism").mkdir()
    (tmp_path / ".prism" / "AGENTS.md").write_text("project: x\nagents: {}\n")
    project_cfg = load_agents_config(tmp_path)
    global_cfg = _global_cfg()
    assignment = resolve_assignment("architect", project_cfg, global_cfg)
    assert assignment is not None
    assert assignment.tool == "claude_code"


def test_resolve_assignment_returns_none_for_unknown_role(project_dir):
    project_cfg = ProjectAgentsConfig()
    global_cfg = PrismConfig()
    assert resolve_assignment("unknown_role", project_cfg, global_cfg) is None


def test_validate_tool_exists_true(project_dir):
    assert validate_tool_exists("claude_code", _global_cfg()) is True


def test_validate_tool_exists_false():
    assert validate_tool_exists("unknown_tool", _global_cfg()) is False


def test_validate_model_exists_true():
    assert validate_model_exists("anthropic.opus", _global_cfg()) is True


def test_validate_model_exists_false():
    assert validate_model_exists("anthropic.nonexistent", _global_cfg()) is False


def test_validate_model_invalid_format():
    assert validate_model_exists("no-dot-format", _global_cfg()) is False


# ── 3.2 Compatibility validator ───────────────────────────────────────────────

def test_compatibility_claude_code_architect():
    result = check_compatibility("architect", "claude_code")
    assert result.compatible is True
    assert result.missing == []


def test_compatibility_copilot_architect_missing_caps():
    result = check_compatibility("architect", "copilot")
    assert result.compatible is False
    assert len(result.missing) > 0
    assert "spec_kit_commands" in result.missing or "flux_mcp" in result.missing


def test_compatibility_missing_caps_have_warnings():
    result = check_compatibility("developer", "copilot")
    assert len(result.warnings) > 0
    assert any("not supported by 'copilot'" in w for w in result.warnings)


def test_compatibility_suggestion_for_incompatible():
    result = check_compatibility("architect", "copilot")
    assert result.suggestion == "claude_code"


def test_compatibility_memory_any_tool():
    for tool in ("claude_code", "opencode", "cursor", "copilot"):
        result = check_compatibility("memory", tool)
        assert result.compatible is True


def test_compatibility_reviewer_opencode():
    result = check_compatibility("reviewer", "opencode")
    assert result.compatible is True


def test_compatibility_reviewer_cursor_missing_flux():
    result = check_compatibility("reviewer", "cursor")
    assert not result.compatible
    assert "flux_mcp" in result.missing


# ── 3.3 Context generator ─────────────────────────────────────────────────────

def test_output_file_for_each_tool():
    assert output_file_for_tool("claude_code") == "CLAUDE.md"
    assert output_file_for_tool("opencode") == "AGENTS.md"
    assert output_file_for_tool("cursor") == ".cursorrules"
    assert output_file_for_tool("gemini") == "GEMINI.md"
    assert output_file_for_tool("windsurf") == ".windsurfrules"
    assert output_file_for_tool("copilot") == ".github/copilot-instructions.md"


def test_generate_context_creates_file(project_dir):
    path = generate_context_file("claude_code", project_dir)
    assert path.exists()
    assert path.name == "CLAUDE.md"


def test_generate_context_has_prism_header(project_dir):
    path = generate_context_file("claude_code", project_dir)
    content = path.read_text()
    assert "AUTO-GENERATED BY PRISM" in content
    assert "claude_code" in content


def test_generate_context_includes_prism_md(project_dir):
    path = generate_context_file("claude_code", project_dir)
    assert "Test Project" in path.read_text()


def test_generate_context_includes_injected_context(project_dir):
    (project_dir / ".prism" / "injected-context.md").write_text("## Injected Memory Context\nskill-xyz")
    path = generate_context_file("claude_code", project_dir)
    assert "skill-xyz" in path.read_text()


def test_generate_context_cursor(project_dir):
    path = generate_context_file("cursor", project_dir)
    assert path.name == ".cursorrules"
    assert "AUTO-GENERATED BY PRISM" in path.read_text()


def test_generate_context_copilot_creates_subdirectory(project_dir):
    path = generate_context_file("copilot", project_dir)
    assert path.parent.name == ".github"
    assert path.exists()


def test_is_manually_edited_returns_false_for_generated(project_dir):
    path = generate_context_file("claude_code", project_dir)
    assert is_manually_edited(path) is False


def test_is_manually_edited_returns_true_for_custom_content(project_dir):
    custom = project_dir / "CLAUDE.md"
    custom.write_text("# My custom instructions\nDo not overwrite this.")
    assert is_manually_edited(custom) is True


def test_is_manually_edited_returns_false_for_missing_file(project_dir):
    assert is_manually_edited(project_dir / "NONEXISTENT.md") is False


# ── 3.4 Launcher ─────────────────────────────────────────────────────────────

def test_prepare_launch_returns_result(project_dir):
    from prism.agents.launcher import prepare_launch
    with patch("prism.agents.launcher._tool_installed", return_value=True), \
         patch("prism.agents.launcher._flux_healthy", return_value=True), \
         patch("prism.agents.launcher._listener_running", return_value=True), \
         patch("prism.agents.launcher._run_inject", return_value=5), \
         patch("prism.config.load_global_config", return_value=_global_cfg()):
        result = prepare_launch("architect", project_dir, skip_inject=True)

    assert result.role == "architect"
    assert result.tool == "claude_code"
    assert result.context_file == "CLAUDE.md"
    assert "claude" in result.launch_command


def test_prepare_launch_warns_when_tool_missing(project_dir):
    from prism.agents.launcher import prepare_launch
    with patch("prism.agents.launcher._tool_installed", return_value=False), \
         patch("prism.agents.launcher._flux_healthy", return_value=False), \
         patch("prism.agents.launcher._listener_running", return_value=False), \
         patch("prism.agents.launcher._run_inject", return_value=0), \
         patch("prism.config.load_global_config", return_value=_global_cfg()):
        result = prepare_launch("architect", project_dir, skip_inject=True)

    assert any("not installed" in w for w in result.warnings)


def test_prepare_launch_uses_fallback_when_primary_missing(project_dir):
    from prism.agents.launcher import prepare_launch

    def _installed(tool):
        return tool == "opencode"

    with patch("prism.agents.launcher._tool_installed", side_effect=_installed), \
         patch("prism.agents.launcher._flux_healthy", return_value=False), \
         patch("prism.agents.launcher._listener_running", return_value=False), \
         patch("prism.agents.launcher._run_inject", return_value=0), \
         patch("prism.config.load_global_config", return_value=_global_cfg()):
        result = prepare_launch("architect", project_dir, skip_inject=True)

    assert result.tool == "opencode"
    assert any("fallback" in w for w in result.warnings)


def test_prepare_launch_warns_flux_not_reachable(project_dir):
    from prism.agents.launcher import prepare_launch
    with patch("prism.agents.launcher._tool_installed", return_value=True), \
         patch("prism.agents.launcher._flux_healthy", return_value=False), \
         patch("prism.agents.launcher._listener_running", return_value=True), \
         patch("prism.agents.launcher._run_inject", return_value=0), \
         patch("prism.config.load_global_config", return_value=_global_cfg()):
        result = prepare_launch("architect", project_dir, skip_inject=True)

    assert any("Flux" in w for w in result.warnings)


def test_prepare_launch_raises_for_unknown_role(project_dir):
    from prism.agents.launcher import prepare_launch
    with patch("prism.config.load_global_config", return_value=PrismConfig()):
        with pytest.raises(ValueError, match="No assignment found"):
            prepare_launch("unknown_role", project_dir, skip_inject=True)


# ── 3.6 End-to-end simulated flow ────────────────────────────────────────────

def test_end_to_end_simulated(project_dir):
    """Full flow: AGENTS.md parse → compatibility → context gen → launch command."""
    from prism.agents.launcher import prepare_launch

    with patch("prism.agents.launcher._tool_installed", return_value=True), \
         patch("prism.agents.launcher._flux_healthy", return_value=True), \
         patch("prism.agents.launcher._listener_running", return_value=True), \
         patch("prism.agents.launcher._run_inject", return_value=7), \
         patch("prism.config.load_global_config", return_value=_global_cfg()):
        result = prepare_launch("architect", project_dir, skip_inject=False)

    assert result.role == "architect"
    assert result.skill_count == 7
    assert result.warnings == []
    ctx = project_dir / result.context_file
    assert ctx.exists()
    assert "AUTO-GENERATED BY PRISM" in ctx.read_text()
    assert "claude" in result.launch_command
