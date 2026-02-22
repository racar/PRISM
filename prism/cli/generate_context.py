from __future__ import annotations

from pathlib import Path

import click
from rich.console import Console

from prism.agents.context_generator import (
    generate_context_file, is_manually_edited, output_file_for_tool,
)
from prism.agents.config import load_agents_config, resolve_assignment
from prism.config import load_global_config

console = Console()

_ROLES = ["architect", "developer", "reviewer", "memory", "optimizer"]


@click.command(name="generate-context")
@click.option("--role", type=click.Choice(_ROLES), default=None,
              help="Generate for a specific agent role (defaults to all configured roles)")
@click.option("--project-dir", default=".", type=click.Path(), show_default=True)
@click.option("--force", is_flag=True, help="Overwrite even if manually edited")
def generate_context(role: str | None, project_dir: str, force: bool) -> None:
    """Generate tool-specific context file (CLAUDE.md, .cursorrules, etc.)."""
    proj_dir = Path(project_dir).resolve()
    global_cfg = load_global_config()
    project_cfg = load_agents_config(proj_dir)

    roles = [role] if role else list(project_cfg.agents.keys()) or _ROLES[:1]
    seen_tools: set[str] = set()

    for r in roles:
        assignment = resolve_assignment(r, project_cfg, global_cfg)
        if assignment is None:
            console.print(f"[yellow]  ⚠  No assignment for role '{r}' — skipping[/yellow]")
            continue
        tool = assignment.tool
        if tool in seen_tools:
            continue
        seen_tools.add(tool)
        _generate_for_tool(tool, proj_dir, force)


def _generate_for_tool(tool: str, proj_dir: Path, force: bool) -> None:
    out_rel = output_file_for_tool(tool)
    out_path = proj_dir / out_rel
    if not force and is_manually_edited(out_path):
        console.print(f"  [yellow]⚠  {out_rel} was manually edited — skipping (use --force to overwrite)[/yellow]")
        return
    path = generate_context_file(tool, proj_dir)
    console.print(f"  [green]✅ {path.relative_to(proj_dir)}[/green] (tool: {tool})")
