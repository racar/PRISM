from __future__ import annotations

from pathlib import Path
from typing import Optional

import yaml
from pydantic import BaseModel, Field

GLOBAL_CONFIG_DIR = Path.home() / ".prism"
GLOBAL_CONFIG_PATH = GLOBAL_CONFIG_DIR / "prism.config.yaml"


class ToolConfig(BaseModel):
    command: str
    context_file: str
    mcp_support: bool = False


class AgentRoleAssignment(BaseModel):
    tool: str
    model: str
    reason: Optional[str] = None
    fallback: Optional[AgentRoleAssignment] = None


AgentRoleAssignment.model_rebuild()


class AgentRoleDefault(BaseModel):
    default: AgentRoleAssignment


class MemoryConfig(BaseModel):
    global_path: str = "~/.prism/memory"
    git_remote: str = ""
    auto_commit: bool = True
    embeddings_enabled: bool = False


class FluxConfig(BaseModel):
    url: str = "http://localhost:9000"
    mcp_command: str = "docker run -i --rm -v flux-data:/app/packages/data flux-mcp"


class PrismConfig(BaseModel):
    version: str = "1.0"
    tools: dict[str, ToolConfig] = Field(default_factory=dict)
    models: dict[str, dict[str, str]] = Field(default_factory=dict)
    agent_roles: dict[str, AgentRoleDefault] = Field(default_factory=dict)
    memory: MemoryConfig = Field(default_factory=MemoryConfig)
    flux: FluxConfig = Field(default_factory=FluxConfig)


class ProjectConfig(BaseModel):
    name: str = ""
    description: str = ""
    version: str = "0.1.0"
    created: str = ""
    stack: list[str] = Field(default_factory=list)
    flux_project_id: str = ""
    agent_roles: dict[str, AgentRoleDefault] = Field(default_factory=dict)


def _read_yaml(path: Path) -> dict:
    if not path.exists():
        return {}
    with open(path) as f:
        return yaml.safe_load(f) or {}


def load_global_config() -> PrismConfig:
    data = _read_yaml(GLOBAL_CONFIG_PATH)
    return PrismConfig.model_validate(data) if data else PrismConfig()


def load_project_config(project_dir: Path) -> ProjectConfig:
    data = _read_yaml(project_dir / ".prism" / "project.yaml")
    return ProjectConfig.model_validate(data) if data else ProjectConfig()


def resolve_agent_roles(
    global_cfg: PrismConfig, project_cfg: ProjectConfig
) -> dict[str, AgentRoleDefault]:
    roles = dict(global_cfg.agent_roles)
    roles.update(project_cfg.agent_roles)
    return roles
