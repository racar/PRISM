from __future__ import annotations

import hashlib
from pathlib import Path

import click
import yaml
from rich.console import Console

from prism.board.flux_client import FluxClient
from prism.board.task_mapper import parse_tasks_md
from prism.config import load_project_config
from prism.spec.augmenter import is_augmented

console = Console()


@click.command()
@click.option("--project-id", default="", help="Flux project ID (overrides project.yaml)")
@click.option("--project-dir", default=".", type=click.Path(), show_default=True)
@click.option("--dry-run", is_flag=True, help="Preview without creating tasks in Flux")
def sync(project_id: str, project_dir: str, dry_run: bool) -> None:
    """Sync tasks.md to Flux Backlog."""
    proj_dir = Path(project_dir).resolve()
    client = FluxClient()
    if not dry_run and not client.healthy():
        raise click.ClickException("Flux is not reachable. Run: prism board setup")

    source = _resolve_tasks_file(proj_dir)
    epics = parse_tasks_md(source)
    flux_id = project_id or load_project_config(proj_dir).flux_project_id
    if not flux_id and not dry_run:
        raise click.ClickException(
            "flux_project_id not set. Use --project-id or set it in .prism/project.yaml"
        )

    mapping = _load_mapping(proj_dir)
    _normalize_mapping(mapping)
    counts = _sync_epics(epics, flux_id, client, mapping, dry_run)
    if not dry_run:
        _save_mapping(proj_dir, mapping)
    console.print(
        f"[green]✅ Synced {counts['created']} created, "
        f"{counts['updated']} updated to Flux Backlog[/green]"
    )


def _resolve_tasks_file(proj_dir: Path) -> Path:
    augmented = proj_dir / ".prism" / "spec" / "tasks.prism.md"
    if augmented.exists():
        return augmented
    latest = next(proj_dir.rglob("tasks.md"), None)
    if latest is None:
        raise click.ClickException("No tasks.md found. Run: prism augment")
    return latest


def _load_mapping(proj_dir: Path) -> dict:
    yaml_path = proj_dir / ".prism" / "project.yaml"
    if not yaml_path.exists():
        return {}
    data = yaml.safe_load(yaml_path.read_text(encoding="utf-8")) or {}
    return data.get("flux_task_map", {})


def _save_mapping(proj_dir: Path, mapping: dict) -> None:
    yaml_path = proj_dir / ".prism" / "project.yaml"
    data = (
        yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
        if yaml_path.exists()
        else {}
    )
    data["flux_task_map"] = mapping
    yaml_path.write_text(
        yaml.dump(data, default_flow_style=False), encoding="utf-8"
    )


def _normalize_mapping(mapping: dict) -> None:
    for key, value in list(mapping.items()):
        if key.startswith("__epic__"):
            continue
        if isinstance(value, str):
            mapping[key] = {"flux_id": value, "content_hash": ""}


def _task_content_hash(task) -> str:
    blob = f"{task.title}|{task.description}|{'|'.join(task.criteria)}"
    return hashlib.sha256(blob.encode()).hexdigest()[:16]


def _task_changed(task, mapping: dict) -> bool:
    entry = mapping.get(task.title)
    if not entry or not isinstance(entry, dict):
        return True
    return entry.get("content_hash", "") != _task_content_hash(task)


def _task_body(task) -> str:
    return f"{task.description}\n\n" + "".join(
        f"- [ ] {c}\n" for c in task.criteria
    )


def _sync_epics(
    epics, flux_id: str, client: FluxClient, mapping: dict, dry_run: bool,
) -> dict:
    counts = {"created": 0, "updated": 0}
    for epic in epics:
        epic_flux_id = _ensure_epic(epic, flux_id, client, mapping, dry_run)
        for task in epic.tasks:
            result = _sync_single_task(
                task, flux_id, epic_flux_id, client, mapping, dry_run,
            )
            if result in counts:
                counts[result] += 1
    return counts


def _sync_single_task(
    task, flux_id: str, epic_id: str,
    client: FluxClient, mapping: dict, dry_run: bool,
) -> str:
    if task.title not in mapping:
        _create_task(task, flux_id, epic_id, client, mapping, dry_run)
        return "created"
    if _task_changed(task, mapping):
        _update_task(task, client, mapping, dry_run)
        return "updated"
    console.print(f"  [dim]skip (unchanged): {task.title}[/dim]")
    return "skip"


def _ensure_epic(
    epic, flux_id: str, client: FluxClient, mapping: dict, dry_run: bool,
) -> str:
    key = f"__epic__{epic.title}"
    if key in mapping:
        return mapping[key]
    if dry_run:
        console.print(f"  [dim][dry-run] epic: {epic.title}[/dim]")
        return "dry-run-epic"
    flux_epic = client.create_epic(flux_id, epic.title, epic.description)
    mapping[key] = flux_epic.id
    return flux_epic.id


def _create_task(
    task, flux_id: str, epic_id: str,
    client: FluxClient, mapping: dict, dry_run: bool,
) -> None:
    body = _task_body(task)
    if dry_run:
        console.print(f"  [dim][dry-run] task: {task.title}[/dim]")
        return
    flux_task = client.create_task(flux_id, task.title, body, epic_id)
    mapping[task.title] = {
        "flux_id": flux_task.id,
        "content_hash": _task_content_hash(task),
    }
    console.print(f"  [green]+ {task.title}[/green]")


def _update_task(
    task, client: FluxClient, mapping: dict, dry_run: bool,
) -> None:
    entry = mapping.get(task.title, {})
    flux_id = entry.get("flux_id", "") if isinstance(entry, dict) else entry
    body = _task_body(task)
    if dry_run:
        console.print(f"  [dim][dry-run] update: {task.title}[/dim]")
        return
    client.update_task(flux_id, title=task.title, description=body)
    mapping[task.title] = {
        "flux_id": flux_id,
        "content_hash": _task_content_hash(task),
    }
    console.print(f"  [yellow]~ {task.title}[/yellow]")
