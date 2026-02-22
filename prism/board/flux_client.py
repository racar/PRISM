from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Optional

import httpx

from prism.config import load_global_config

_RETRY_DELAYS = (0, 1, 2, 4)


@dataclass
class Task:
    id: str
    title: str
    status: str
    description: str = ""
    epic_id: Optional[str] = None
    project_id: Optional[str] = None


@dataclass
class Epic:
    id: str
    title: str
    description: str = ""
    project_id: Optional[str] = None


@dataclass
class Webhook:
    id: str
    url: str
    events: list[str] = field(default_factory=list)


def _flux_url() -> str:
    return load_global_config().flux.url


def _request(method: str, path: str, **kwargs) -> dict:
    url = f"{_flux_url()}{path}"
    last_exc: Exception | None = None
    for delay in _RETRY_DELAYS:
        if delay:
            time.sleep(delay)
        try:
            resp = httpx.request(method, url, timeout=10, **kwargs)
            resp.raise_for_status()
            return resp.json()
        except Exception as exc:
            last_exc = exc
    raise RuntimeError(f"Flux request failed after retries: {last_exc}")


def _to_task(data: dict, project_id: str | None = None) -> Task:
    return Task(
        id=data["id"], title=data["title"], status=data["status"],
        description=data.get("description", ""),
        epic_id=data.get("epicId"), project_id=project_id or data.get("projectId"),
    )


def _to_epic(data: dict, project_id: str | None = None) -> Epic:
    return Epic(
        id=data["id"], title=data["title"],
        description=data.get("description", ""),
        project_id=project_id or data.get("projectId"),
    )


class FluxClient:
    def healthy(self) -> bool:
        try:
            httpx.get(f"{_flux_url()}/health", timeout=3).raise_for_status()
            return True
        except Exception:
            return False

    def create_project(self, name: str) -> dict:
        return _request("POST", "/api/projects", json={"name": name})

    def create_epic(self, project_id: str, title: str, description: str = "") -> Epic:
        data = _request("POST", f"/api/projects/{project_id}/epics",
                        json={"title": title, "description": description})
        return _to_epic(data, project_id)

    def create_task(self, project_id: str, title: str, body: str = "",
                    epic_id: Optional[str] = None) -> Task:
        payload: dict = {"title": title, "description": body, "status": "todo"}
        if epic_id:
            payload["epicId"] = epic_id
        data = _request("POST", f"/api/projects/{project_id}/tasks", json=payload)
        return _to_task(data, project_id)

    def get_task(self, task_id: str) -> Task:
        return _to_task(_request("GET", f"/api/tasks/{task_id}"))

    def move_task(self, task_id: str, status: str) -> Task:
        return _to_task(_request("PATCH", f"/api/tasks/{task_id}", json={"status": status}))

    def list_tasks(self, project_id: str, status: Optional[str] = None) -> list[Task]:
        params = {"status": status} if status else {}
        data = _request("GET", f"/api/projects/{project_id}/tasks", params=params)
        items = data if isinstance(data, list) else data.get("tasks", [])
        return [_to_task(t, project_id) for t in items]

    def list_epics(self, project_id: str) -> list[Epic]:
        data = _request("GET", f"/api/projects/{project_id}/epics")
        items = data if isinstance(data, list) else data.get("epics", [])
        return [_to_epic(e, project_id) for e in items]

    def add_webhook(self, url: str, events: list[str]) -> Webhook:
        data = _request("POST", "/api/webhooks", json={"url": url, "events": events})
        return Webhook(id=data["id"], url=data["url"], events=data.get("events", events))
