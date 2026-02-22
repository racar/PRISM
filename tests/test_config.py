from pathlib import Path

import pytest

from prism.config import (
    AgentRoleAssignment,
    AgentRoleDefault,
    PrismConfig,
    ProjectConfig,
    load_global_config,
    load_project_config,
    resolve_agent_roles,
)


def test_prism_config_defaults():
    cfg = PrismConfig()
    assert cfg.version == "1.0"
    assert cfg.tools == {}
    assert cfg.memory.auto_commit is True
    assert cfg.memory.global_path == "~/.prism/memory"


def test_prism_config_parses_tools():
    data = {
        "version": "1.0",
        "tools": {
            "claude_code": {
                "command": "claude",
                "context_file": "CLAUDE.md",
                "mcp_support": True,
            }
        },
    }
    cfg = PrismConfig.model_validate(data)
    assert cfg.tools["claude_code"].command == "claude"
    assert cfg.tools["claude_code"].mcp_support is True


def test_prism_config_parses_agent_roles():
    data = {
        "agent_roles": {
            "architect": {"default": {"tool": "claude_code", "model": "anthropic.opus"}}
        }
    }
    cfg = PrismConfig.model_validate(data)
    assert cfg.agent_roles["architect"].default.tool == "claude_code"
    assert cfg.agent_roles["architect"].default.model == "anthropic.opus"


def test_project_config_defaults():
    cfg = ProjectConfig()
    assert cfg.name == ""
    assert cfg.stack == []
    assert cfg.agent_roles == {}


def test_load_global_config_missing_file(tmp_prism_global):
    cfg = load_global_config()
    assert isinstance(cfg, PrismConfig)


def test_load_global_config_reads_file(tmp_prism_global):
    config_path = tmp_prism_global / "prism.config.yaml"
    config_path.write_text('version: "2.0"\n')
    cfg = load_global_config()
    assert cfg.version == "2.0"


def test_load_project_config_missing(tmp_path):
    cfg = load_project_config(tmp_path)
    assert isinstance(cfg, ProjectConfig)
    assert cfg.name == ""


def test_load_project_config_reads_file(tmp_path):
    prism_dir = tmp_path / ".prism"
    prism_dir.mkdir()
    (prism_dir / "project.yaml").write_text("name: my-project\ndescription: Test\n")
    cfg = load_project_config(tmp_path)
    assert cfg.name == "my-project"
    assert cfg.description == "Test"


def test_resolve_agent_roles_global_only():
    global_cfg = PrismConfig(
        agent_roles={
            "architect": AgentRoleDefault(
                default=AgentRoleAssignment(tool="claude_code", model="anthropic.opus")
            )
        }
    )
    roles = resolve_agent_roles(global_cfg, ProjectConfig())
    assert roles["architect"].default.tool == "claude_code"


def test_resolve_agent_roles_project_overrides():
    global_cfg = PrismConfig(
        agent_roles={
            "architect": AgentRoleDefault(
                default=AgentRoleAssignment(tool="claude_code", model="anthropic.opus")
            )
        }
    )
    project_cfg = ProjectConfig(
        agent_roles={
            "architect": AgentRoleDefault(
                default=AgentRoleAssignment(tool="opencode", model="moonshot.kimi")
            )
        }
    )
    roles = resolve_agent_roles(global_cfg, project_cfg)
    assert roles["architect"].default.tool == "opencode"
    assert roles["architect"].default.model == "moonshot.kimi"


def test_resolve_agent_roles_project_adds_new_role():
    global_cfg = PrismConfig()
    project_cfg = ProjectConfig(
        agent_roles={
            "developer": AgentRoleDefault(
                default=AgentRoleAssignment(tool="cursor", model="anthropic.sonnet")
            )
        }
    )
    roles = resolve_agent_roles(global_cfg, project_cfg)
    assert "developer" in roles
    assert roles["developer"].default.tool == "cursor"
