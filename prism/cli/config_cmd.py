from pathlib import Path

import click
import yaml
from rich.console import Console
from rich.syntax import Syntax

from prism.config import load_global_config, load_project_config, resolve_agent_roles

console = Console()


@click.group(name="config")
def config() -> None:
    """Manage PRISM configuration."""


def _print_section(title: str, data: dict) -> None:
    console.print(f"\n[bold blue]{title}[/bold blue]")
    yaml_str = yaml.dump(data, default_flow_style=False, allow_unicode=True)
    console.print(Syntax(yaml_str, "yaml", theme="monokai", line_numbers=False))


@config.command(name="show")
@click.option("--project-dir", default=".", type=click.Path(), show_default=True)
def show(project_dir: str) -> None:
    """Show active PRISM configuration."""
    global_cfg = load_global_config()
    project_cfg = load_project_config(Path(project_dir))
    _print_section("Global Config (~/.prism/prism.config.yaml)", global_cfg.model_dump())
    if project_cfg.name:
        _print_section("Project Config (.prism/project.yaml)", project_cfg.model_dump())
        roles = resolve_agent_roles(global_cfg, project_cfg)
        _print_section("Resolved Agent Roles", {k: v.model_dump() for k, v in roles.items()})
