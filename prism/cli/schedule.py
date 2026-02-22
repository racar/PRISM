"""Scheduler — manage weekly optimizer cron jobs."""

from __future__ import annotations

import getpass
import platform
import subprocess
from pathlib import Path

import click
from rich.console import Console

console = Console()

_CRON_COMMENT = "# PRISM weekly optimizer"
_CRON_JOB = "0 9 * * 0 {} prism optimize --auto > ~/.prism/optimizer.log 2>&1"


def _get_prism_path() -> str:
    """Get the path to the prism executable."""
    # Try to find prism in PATH
    try:
        result = subprocess.run(
            ["which", "prism"], capture_output=True, text=True, check=True
        )
        return result.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        # Fallback: assume it's installed via uv
        return "~/.local/bin/prism"


def _install_cron() -> bool:
    """Install the weekly cron job on Unix systems."""
    try:
        prism_path = _get_prism_path()
        cron_line = f"{_CRON_COMMENT}\n{_CRON_JOB.format(prism_path)}"

        # Get existing crontab
        try:
            current = subprocess.run(
                ["crontab", "-l"], capture_output=True, text=True, check=True
            )
            existing = current.stdout
        except subprocess.CalledProcessError:
            existing = ""

        # Check if already installed
        if "PRISM weekly optimizer" in existing:
            console.print("[yellow]Cron job already installed[/yellow]")
            return True

        # Add new cron job
        new_crontab = existing + "\n" + cron_line + "\n"

        subprocess.run(["crontab", "-"], input=new_crontab, text=True, check=True)

        return True
    except Exception as exc:
        console.print(f"[red]Failed to install cron: {exc}[/red]")
        return False


def _uninstall_cron() -> bool:
    """Remove the weekly cron job on Unix systems."""
    try:
        # Get existing crontab
        result = subprocess.run(["crontab", "-l"], capture_output=True, text=True)

        if result.returncode != 0:
            console.print("[yellow]No crontab found[/yellow]")
            return True

        existing = result.stdout

        # Remove PRISM lines
        lines = existing.split("\n")
        filtered = []
        skip_next = False

        for line in lines:
            if skip_next:
                skip_next = False
                continue
            if "PRISM weekly optimizer" in line:
                skip_next = True  # Skip the actual job line too
                continue
            filtered.append(line)

        new_crontab = "\n".join(filtered)

        subprocess.run(["crontab", "-"], input=new_crontab, text=True, check=True)

        return True
    except Exception as exc:
        console.print(f"[red]Failed to uninstall cron: {exc}[/red]")
        return False


def _is_cron_installed() -> bool:
    """Check if the PRISM cron job is installed."""
    try:
        result = subprocess.run(["crontab", "-l"], capture_output=True, text=True)

        if result.returncode != 0:
            return False

        return "PRISM weekly optimizer" in result.stdout
    except Exception:
        return False


def _install_windows_task() -> bool:
    """Install Windows Task Scheduler job."""
    try:
        # Create XML task definition
        user = getpass.getuser()
        prism_path = _get_prism_path()

        task_xml = f"""<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.2" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo>
    <Description>PRISM Weekly Memory Optimizer</Description>
  </RegistrationInfo>
  <Triggers>
    <CalendarTrigger>
      <StartBoundary>2025-01-01T09:00:00</StartBoundary>
      <ScheduleByWeek>
        <DaysOfWeek>
          <Sunday />
        </DaysOfWeek>
        <WeeksInterval>1</WeeksInterval>
      </ScheduleByWeek>
    </CalendarTrigger>
  </Triggers>
  <Principals>
    <Principal id="Author">
      <UserId>{user}</UserId>
      <LogonType>InteractiveToken</LogonType>
    </Principal>
  </Principals>
  <Settings>
    <Enabled>true</Enabled>
    <AllowStartOnDemand>true</AllowStartOnDemand>
  </Settings>
  <Actions Context="Author">
    <Exec>
      <Command>{prism_path}</Command>
      <Arguments>optimize --auto</Arguments>
    </Exec>
  </Actions>
</Task>"""

        xml_path = Path.home() / ".prism" / "optimizer_task.xml"
        xml_path.parent.mkdir(parents=True, exist_ok=True)
        xml_path.write_text(task_xml, encoding="utf-16")

        # Register task
        subprocess.run(
            [
                "schtasks",
                "/create",
                "/tn",
                "PRISM-Optimizer",
                "/xml",
                str(xml_path),
                "/f",
            ],
            check=True,
            capture_output=True,
        )

        return True
    except Exception as exc:
        console.print(f"[red]Failed to install Windows task: {exc}[/red]")
        return False


def _uninstall_windows_task() -> bool:
    """Remove Windows Task Scheduler job."""
    try:
        subprocess.run(
            ["schtasks", "/delete", "/tn", "PRISM-Optimizer", "/f"],
            check=True,
            capture_output=True,
        )
        return True
    except Exception as exc:
        console.print(f"[red]Failed to uninstall Windows task: {exc}[/red]")
        return False


def _is_windows_task_installed() -> bool:
    """Check if Windows task is installed."""
    try:
        result = subprocess.run(
            ["schtasks", "/query", "/tn", "PRISM-Optimizer"],
            capture_output=True,
            text=True,
        )
        return result.returncode == 0
    except Exception:
        return False


@click.group(name="schedule")
def schedule() -> None:
    """Manage the weekly optimizer scheduler."""


@schedule.command(name="enable")
def enable() -> None:
    """Install weekly cron job for prism optimize --auto."""
    system = platform.system()

    if system == "Windows":
        if _install_windows_task():
            console.print("[green]✅ Windows Task Scheduler job installed[/green]")
            console.print("   Runs: Every Sunday at 9:00 AM")
            console.print("   Command: prism optimize --auto")
        else:
            raise click.ClickException("Failed to install Windows task")
    else:
        # Unix-like (Linux, macOS)
        if _install_cron():
            console.print("[green]✅ Cron job installed[/green]")
            console.print("   Runs: Every Sunday at 9:00 AM")
            console.print("   Command: prism optimize --auto")
        else:
            raise click.ClickException("Failed to install cron job")


@schedule.command(name="disable")
def disable() -> None:
    """Remove the optimizer cron job."""
    system = platform.system()

    if system == "Windows":
        if _uninstall_windows_task():
            console.print("[green]✅ Windows Task Scheduler job removed[/green]")
        else:
            raise click.ClickException("Failed to remove Windows task")
    else:
        if _uninstall_cron():
            console.print("[green]✅ Cron job removed[/green]")
        else:
            raise click.ClickException("Failed to remove cron job")


@schedule.command(name="status")
def status() -> None:
    """Check if the scheduler is enabled."""
    system = platform.system()

    if system == "Windows":
        installed = _is_windows_task_installed()
    else:
        installed = _is_cron_installed()

    if installed:
        console.print("[green]✅ Scheduler is enabled[/green]")
        console.print("   Runs: Every Sunday at 9:00 AM")
        console.print("   Command: prism optimize --auto")
    else:
        console.print("[yellow]⚠ Scheduler is not enabled[/yellow]")
        console.print("   Run: prism schedule enable")
