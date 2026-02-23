from __future__ import annotations

from pathlib import Path
from typing import Optional

import yaml
from pydantic import BaseModel

from prism.config import PrismConfig, load_global_config


class AgentAssignment(BaseModel):
    tool: str
    model: str
    reason: Optional[str] = None
    fallback: Optional[AgentAssignment] = None


AgentAssignment.model_rebuild()


class ProjectAgentsConfig(BaseModel):
    project: str = ""
    version: str = "1.0"
    agents: dict[str, AgentAssignment] = {}


def load_agents_config(project_dir: Path) -> ProjectAgentsConfig:
    path = project_dir / ".prism" / "AGENTS.md"
    if not path.exists():
        return ProjectAgentsConfig()
    try:
        data = yaml.safe_load(path.read_text()) or {}
    except yaml.YAMLError:
        # File exists but is not valid YAML (e.g., markdown instructions)
        return ProjectAgentsConfig()
    agents_raw = data.get("agents", {})
    agents = {
        role: AgentAssignment.model_validate(v) for role, v in agents_raw.items() if v
    }
    return ProjectAgentsConfig(
        project=data.get("project", ""),
        version=str(data.get("version", "1.0")),
        agents=agents,
    )


def resolve_assignment(
    role: str, project_cfg: ProjectAgentsConfig, global_cfg: PrismConfig
) -> Optional[AgentAssignment]:
    if role in project_cfg.agents:
        return project_cfg.agents[role]
    role_default = global_cfg.agent_roles.get(role)
    if role_default:
        d = role_default.default
        return AgentAssignment(tool=d.tool, model=d.model, reason=d.reason)
    return None


def validate_tool_exists(tool: str, global_cfg: PrismConfig) -> bool:
    return tool in global_cfg.tools


def validate_model_format(model: str) -> bool:
    return "." in model and len(model.split(".", 1)) == 2


def validate_model_exists(model: str, global_cfg: PrismConfig) -> bool:
    if not validate_model_format(model):
        return False
    provider, alias = model.split(".", 1)
    return provider in global_cfg.models and alias in global_cfg.models[provider]
