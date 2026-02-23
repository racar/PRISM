from __future__ import annotations

import os
import signal
import subprocess
import sys
import socket
from pathlib import Path

import click
from rich.console import Console

import yaml

from prism.config import load_global_config
from prism.project import check_docker

console = Console()

_PID_FILE = ".prism/listener.pid"
_LOG_FILE = Path.home() / ".prism" / "listener.log"


@click.group(name="board")
def board() -> None:
    """Manage Flux Kanban board integration."""


@board.command(name="setup")
@click.option("--project-id", default="", help="Flux project ID (creates one if empty)")
@click.option("--project-dir", default=".", type=click.Path())
def setup(project_id: str, project_dir: str) -> None:
    """Launch Flux via Docker, register MCP, and configure project."""
    if not check_docker():
        raise click.ClickException("Docker is not installed or not running.")
    _start_flux_container()
    _register_mcp()
    proj_dir = Path(project_dir).resolve()
    _configure_webhook(proj_dir)
    _ensure_flux_project(proj_dir, project_id)
    console.print("[green]✅ Flux board ready at http://localhost:9000[/green]")


def _is_port_in_use(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(("127.0.0.1", port)) == 0


@board.command(name="listen")
@click.option("--daemon", is_flag=True, help="Run in background")
@click.option("--port", default=8765, show_default=True)
@click.option("--project-dir", default=".", type=click.Path())
def listen(daemon: bool, port: int, project_dir: str) -> None:
    """Start webhook listener + file watcher for Flux events."""
    proj_dir = Path(project_dir).resolve()

    pid_file = proj_dir / _PID_FILE
    if pid_file.exists():
        try:
            pid = int(pid_file.read_text().strip())
            if _pid_alive(pid):
                console.print(
                    f"[yellow]Listener is already running (PID: {pid})[/yellow]"
                )
                return
        except ValueError:
            pass  # invalid pid file

    if _is_port_in_use(port):
        console.print(
            f"[yellow]⚠ Port {port} is already in use. Is another listener running?[/yellow]"
        )
        return

    if daemon:
        _start_daemon(port, proj_dir)
    else:
        _run_foreground(port, proj_dir)


@board.command(name="stop")
@click.option("--project-dir", default=".", type=click.Path())
def stop(project_dir: str) -> None:
    """Stop the webhook listener process."""
    pid_file = Path(project_dir).resolve() / _PID_FILE
    if not pid_file.exists():
        raise click.ClickException("No listener PID file found. Is it running?")
    pid = int(pid_file.read_text().strip())
    try:
        os.kill(pid, signal.SIGTERM)
        pid_file.unlink()
        console.print(f"[green]✅ Listener (PID {pid}) stopped[/green]")
    except ProcessLookupError:
        pid_file.unlink(missing_ok=True)
        raise click.ClickException(f"Process {pid} not found — already stopped?")


@board.command(name="status")
@click.option("--project-dir", default=".", type=click.Path())
def status(project_dir: str) -> None:
    """Show listener status and last event."""
    pid_file = Path(project_dir).resolve() / _PID_FILE
    if not pid_file.exists():
        console.print("[yellow]Listener: not running[/yellow]")
        return
    pid = int(pid_file.read_text().strip())
    running = _pid_alive(pid)
    state = (
        f"[green]running (PID {pid})[/green]"
        if running
        else "[red]dead (stale PID)[/red]"
    )
    console.print(f"Listener: {state}")
    flux_url = load_global_config().flux.url
    console.print(f"Webhook endpoint: {flux_url.replace('9000', '8765')}/webhook/flux")
    if _LOG_FILE.exists():
        console.print(f"Log: {_LOG_FILE}")


def _ensure_flux_project(proj_dir: Path, project_id: str) -> None:
    if project_id:
        _save_flux_project_id(proj_dir, project_id)
        return
    cfg = load_global_config()
    existing = cfg.flux.url
    proj_cfg_path = proj_dir / ".prism" / "project.yaml"
    if proj_cfg_path.exists():
        data = (
            yaml.safe_load(
                proj_cfg_path.read_text(encoding="utf-8"),
            )
            or {}
        )
        if data.get("flux_project_id"):
            return
    name = proj_dir.name
    _create_and_save_project(proj_dir, name)


def _create_and_save_project(proj_dir: Path, name: str) -> None:
    from prism.board.flux_client import FluxClient

    client = FluxClient()
    if not client.healthy():
        console.print(
            "[yellow]⚠  Flux not reachable — skipping project creation[/yellow]"
        )
        return
    result = client.create_project(name)
    pid = result.get("id", "")
    _save_flux_project_id(proj_dir, pid)
    console.print(f"[green]✅ Flux project '{name}' created ({pid})[/green]")


def _save_flux_project_id(proj_dir: Path, project_id: str) -> None:
    yaml_path = proj_dir / ".prism" / "project.yaml"
    yaml_path.parent.mkdir(parents=True, exist_ok=True)
    data = (
        yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
        if yaml_path.exists()
        else {}
    ) or {}
    data["flux_project_id"] = project_id
    yaml_path.write_text(
        yaml.dump(data, default_flow_style=False),
        encoding="utf-8",
    )


def _validate_docker_image(image: str) -> bool:
    result = subprocess.run(
        ["docker", "image", "inspect", image],
        capture_output=True,
    )
    return result.returncode == 0


def _flux_container_exists() -> bool:
    return (
        subprocess.run(
            ["docker", "inspect", "flux-web"],
            capture_output=True,
        ).returncode
        == 0
    )


def _run_flux_container() -> None:
    cmd = [
        "docker",
        "run",
        "-d",
        "-p",
        "9000:3000",
        "-v",
        "flux-data:/app/packages/data",
        "--name",
        "flux-web",
        "flux-mcp",
        "node",
        "packages/server/dist/index.js",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise click.ClickException(f"Failed to start Flux: {result.stderr}")


def _start_flux_container() -> None:
    if _flux_container_exists():
        console.print("[dim]Flux container already running[/dim]")
        return
    if not _validate_docker_image("flux-mcp"):
        raise click.ClickException(
            "Docker image 'flux-mcp' not found. Build or pull it first."
        )
    _run_flux_container()
    console.print("[green]✅ Flux container started[/green]")


def _register_mcp() -> None:
    cfg = load_global_config().flux
    result = subprocess.run(
        ["claude", "mcp", "add", "flux", "--", *cfg.mcp_command.split()],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        console.print(
            f"[yellow]⚠  MCP registration skipped: {result.stderr.strip()}[/yellow]"
        )
    else:
        console.print("[green]✅ Flux MCP registered with Claude Code[/green]")


def _configure_webhook(proj_dir: Path) -> None:
    try:
        from prism.board.flux_client import FluxClient

        client = FluxClient()
        if not client.healthy():
            console.print(
                "[yellow]⚠  Flux not reachable yet — register webhook manually[/yellow]"
            )
            return
        client.add_webhook(
            "http://localhost:8765/webhook/flux", ["task.status_changed"]
        )
        console.print("[green]✅ Webhook registered in Flux[/green]")
    except Exception as exc:
        console.print(f"[yellow]⚠  Webhook registration failed: {exc}[/yellow]")


def _start_daemon(port: int, proj_dir: Path) -> None:
    _LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    pid_file = proj_dir / _PID_FILE
    pid_file.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        sys.argv[0],
        "board",
        "listen",
        "--port",
        str(port),
        "--project-dir",
        str(proj_dir),
    ]
    with open(_LOG_FILE, "a") as lf:
        proc = subprocess.Popen(cmd, stdout=lf, stderr=lf, start_new_session=True)
    pid_file.write_text(str(proc.pid))
    console.print(f"[green]✅ Listener started (PID: {proc.pid})[/green]")
    console.print(f"   Logs  : {_LOG_FILE}")
    console.print(f"   Stop  : prism board stop")


def _run_foreground(port: int, proj_dir: Path) -> None:
    import threading
    import uvicorn
    from prism.board.webhook_listener import app, set_project_dir
    from prism.spec.watcher import start_watcher

    set_project_dir(proj_dir)
    specs_dir = proj_dir / ".prism" / "spec"
    watcher = start_watcher(specs_dir) if specs_dir.exists() else None

    console.print(
        f"[bold green]PRISM listener[/bold green] on :{port} | project: {proj_dir.name}"
    )
    console.print("  Webhook : POST /webhook/flux")
    console.print("  Press CTRL+C to stop\n")
    try:
        uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
    finally:
        if watcher:
            watcher.stop()


def _pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except (ProcessLookupError, PermissionError):
        return False
