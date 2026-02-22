from __future__ import annotations

import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Optional

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ValidationError

log = logging.getLogger("prism.listener")

app = FastAPI(title="PRISM Webhook Listener", version="1.0")
_DISPATCH_TIMEOUT = 30
_executor = ThreadPoolExecutor(max_workers=2)

_project_dir: Optional[Path] = None


def set_project_dir(path: Path) -> None:
    global _project_dir
    _project_dir = path


# ── Payload models ────────────────────────────────────────────────────────────

class _TaskPayload(BaseModel):
    id: str
    title: str
    status: str
    description: str = ""
    epic_id: Optional[str] = None


class _TransitionPayload(BaseModel):
    task: _TaskPayload
    previous: dict[str, Any] = {}


class FluxWebhookPayload(BaseModel):
    event: str
    data: _TransitionPayload


# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/health")
def health() -> dict:
    return {"status": "ok", "project_dir": str(_project_dir)}


@app.exception_handler(ValidationError)
async def _validation_error_handler(request: Request, exc: ValidationError) -> JSONResponse:
    return JSONResponse(status_code=422, content={"detail": str(exc)})


@app.post("/webhook/flux")
async def handle_flux_event(payload: FluxWebhookPayload) -> dict:
    if payload.event != "task.status_changed":
        return {"handled": False}
    prev = payload.data.previous.get("status", "")
    curr = payload.data.task.status
    log.info("[webhook] %s → %s | task=%s", prev, curr, payload.data.task.id)
    await _safe_dispatch(prev, curr, payload.data.task)
    return {"handled": True, "transition": f"{prev}→{curr}"}


# ── Transition handlers ───────────────────────────────────────────────────────

async def _safe_dispatch(prev: str, curr: str, task: _TaskPayload) -> None:
    loop = asyncio.get_running_loop()
    try:
        await asyncio.wait_for(
            loop.run_in_executor(_executor, _dispatch_transition, prev, curr, task),
            timeout=_DISPATCH_TIMEOUT,
        )
    except asyncio.TimeoutError:
        log.error("[webhook] dispatch timed out after %ds for task %s", _DISPATCH_TIMEOUT, task.id)
    except Exception as exc:
        log.error("[webhook] dispatch error: %s", exc)


def _dispatch_transition(prev: str, curr: str, task: _TaskPayload) -> None:
    if prev == "todo" and curr == "doing":
        _on_task_started(task)
    elif curr == "done":
        _on_task_done(task)
    elif curr == "review":
        log.info("[webhook] task %s ready for review", task.id)


def _on_task_started(task: _TaskPayload) -> None:
    if _project_dir is None:
        log.warning("[webhook] project_dir not set — cannot generate current-task.md")
        return
    try:
        from prism.board.task_mapper import generate_current_task_md
        path = generate_current_task_md(task, _project_dir)
        log.info("[webhook] current-task.md generated → %s", path)
    except Exception as exc:
        log.error("[webhook] current-task.md generation failed: %s", exc)


def _on_task_done(task: _TaskPayload) -> None:
    log.info("[webhook] task %s done — memory capture queued (Fase 3)", task.id)
