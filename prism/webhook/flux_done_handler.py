"""Flux Done Handler - Processes webhooks when tasks move to Done.

This handler triggers the PRISM pipeline when a task is completed.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from prism.pipeline.orchestrator import PipelineOrchestrator, PipelineResult


router = APIRouter()


class FluxWebhookPayload(BaseModel):
    """Payload from Flux webhook."""

    event: str  # "task_moved", "task_created", etc.
    task_id: str
    from_status: Optional[str] = None
    to_status: Optional[str] = None  # "Done", "In Progress", etc.
    project_id: str
    user: str  # Who triggered the action
    task_title: Optional[str] = None
    task_body: Optional[str] = None


class FluxDoneResponse(BaseModel):
    """Response to Flux webhook."""

    status: str
    pr_number: Optional[int] = None
    container_name: Optional[str] = None
    message: str


@router.post("/webhook/flux/task-moved", response_model=FluxDoneResponse)
async def handle_task_moved(payload: FluxWebhookPayload) -> FluxDoneResponse:
    """Handle task moved webhook from Flux.

    Only processes when task is moved to Done by a PRISM agent.
    """
    # Only process if moved to Done
    if payload.to_status != "Done":
        return FluxDoneResponse(
            status="ignored",
            message=f"Not moved to Done (to_status={payload.to_status})",
        )

    # Only process PRISM agent actions (not human actions)
    # PRISM agents use usernames like "prism-developer", "prism-architect", etc.
    if not payload.user.startswith("prism-"):
        return FluxDoneResponse(
            status="ignored",
            message="Not a PRISM agent action",
        )

    # Start pipeline
    orchestrator = PipelineOrchestrator()

    try:
        result = orchestrator.process_task_done(payload.task_id)

        if result.success:
            return FluxDoneResponse(
                status="success",
                pr_number=result.pr.number if result.pr else None,
                container_name=result.container.name if result.container else None,
                message="Pipeline completed. Ready for QA review.",
            )
        else:
            return FluxDoneResponse(
                status="failed",
                message=result.message,
            )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/webhook/flux/container-ready")
async def handle_container_ready(payload: dict) -> dict:
    """Handle notification that test container is ready.

    This is called by the container itself after quality gates pass.
    """
    task_id = payload.get("task_id")
    container_status = payload.get("status")

    if not task_id:
        raise HTTPException(status_code=400, detail="task_id required")

    # Update Flux task with container info
    # This would be implemented with Flux MCP

    return {
        "status": "acknowledged",
        "task_id": task_id,
        "container_status": container_status,
    }


@router.post("/webhook/flux/qa-approved")
async def handle_qa_approved(payload: dict) -> dict:
    """Handle QA approval notification."""
    task_id = payload.get("task_id")

    # Update Flux task
    # Move to "Approved" or similar status

    return {
        "status": "acknowledged",
        "task_id": task_id,
        "action": "qa_approved",
    }


@router.post("/webhook/flux/qa-rejected")
async def handle_qa_rejected(payload: dict) -> dict:
    """Handle QA rejection notification."""
    task_id = payload.get("task_id")

    # Update Flux task
    # Move back to "In Progress" or "Backlog"

    return {
        "status": "acknowledged",
        "task_id": task_id,
        "action": "qa_rejected",
    }
