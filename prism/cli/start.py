from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import click
from rich.console import Console

console = Console()

_ROLES = ["architect", "developer", "reviewer", "memory", "optimizer"]


@click.command()
@click.option("--role", required=True, type=click.Choice(_ROLES), help="Agent role to launch")
@click.option("--project-dir", default=".", type=click.Path(), show_default=True)
@click.option("--no-launch", is_flag=True, help="Print the launch command but don't execute it")
@click.option("--skip-inject", is_flag=True, help="Skip running prism inject before launch")
def start(role: str, project_dir: str, no_launch: bool, skip_inject: bool) -> None:
    """Prepare context and launch an agent by role."""
    from prism.agents.launcher import LaunchResult, prepare_launch

    proj_dir = Path(project_dir).resolve()
    if not (proj_dir / ".prism").exists():
        raise click.ClickException("No .prism/ found. Run: prism init or prism attach")

    console.print(f"\n[bold]PRISM[/bold] — starting [cyan]{role}[/cyan] agent\n")
    result = prepare_launch(role, proj_dir, skip_inject=skip_inject)
    _print_checklist(result)
    _print_launch_instructions(result, proj_dir, no_launch)


def _print_checklist(result) -> None:
    _check("Tool", f"{result.tool} ({result.tool} found)", not any("not installed" in w for w in result.warnings))
    _check("Model", result.model, True)
    _check("Flux", "connected", not any("Flux" in w for w in result.warnings))
    _check("Listener", "running", not any("listener" in w.lower() for w in result.warnings))
    _check("Memory", f"{result.skill_count} skills injected", True)
    _check("Context", result.context_file, True)
    for w in result.warnings:
        console.print(f"  [yellow]⚠  {w}[/yellow]")
    console.print()


def _check(label: str, detail: str, ok: bool) -> None:
    icon = "[green]✅[/green]" if ok else "[yellow]⚠ [/yellow]"
    console.print(f"  {icon} [bold]{label}:[/bold] {detail}")


def _print_launch_instructions(result, proj_dir: Path, no_launch: bool) -> None:
    console.print(f"Launch your session with:\n  [bold cyan]{result.launch_command}[/bold cyan]\n")
    if no_launch:
        return
    answer = click.prompt("Press Enter to launch automatically, or n to cancel", default="")
    if answer.strip().lower() != "n":
        _exec_tool(result.launch_command, proj_dir)


def _exec_tool(command: str, cwd: Path) -> None:
    parts = command.split()
    try:
        subprocess.run(parts, cwd=str(cwd), check=False)
    except FileNotFoundError:
        console.print(f"[red]Could not launch '{parts[0]}' — is it installed?[/red]")
