"""Approval Workflow - Manages PR approval/rejection by QA agents."""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from typing import Optional

from prism.pipeline.container_manager import ContainerManager
from prism.pipeline.pr_manager import PRManager


@dataclass
class QAReviewResult:
    """Result of a QA review."""

    pr_number: int
    approved: bool
    message: str
    reviewed_by: str
    task_id: str


class QAApprovalWorkflow:
    """Manages the QA approval workflow for PRs."""

    def __init__(self):
        self.pr_manager = PRManager()
        self.container_manager = ContainerManager()
        self._monitored_prs = {}
        self._results = {}
        self._lock = threading.Lock()

    def start_monitoring(self, pr_number: int, container_name: str, task_id: str):
        """Start monitoring a PR for QA approval.

        Args:
            pr_number: PR number
            container_name: Container name
            task_id: Task ID
        """
        thread = threading.Thread(
            target=self._monitor_pr,
            args=(pr_number, container_name, task_id),
            daemon=True,
        )

        with self._lock:
            self._monitored_prs[pr_number] = thread

        thread.start()

    def _monitor_pr(self, pr_number: int, container_name: str, task_id: str):
        """Monitor PR until QA approves or rejects."""

        max_wait = 3600 * 4  # 4 hours max
        start = time.time()

        while time.time() - start < max_wait:
            with self._lock:
                result = self._results.get(pr_number)

            if result:
                if result.approved:
                    # Approve PR on GitHub
                    try:
                        self.pr_manager.approve_pr(
                            pr_number,
                            result.message,
                            result.reviewed_by,
                        )
                        print(f"✅ PR #{pr_number} aprobado por {result.reviewed_by}")

                        # Notify human
                        self._notify_human_for_merge(pr_number, result)

                    except Exception as e:
                        print(f"❌ Error aprobando PR: {e}")

                else:
                    # Request changes
                    try:
                        self.pr_manager.request_changes(
                            pr_number,
                            result.message,
                            result.reviewed_by,
                        )
                        print(f"❌ PR #{pr_number} rechazado")

                    except Exception as e:
                        print(f"❌ Error rechazando PR: {e}")

                # Keep container for 30 more minutes then destroy
                time.sleep(1800)
                self.container_manager.destroy_container(task_id)
                return

            time.sleep(10)

        # Timeout
        print(f"⏰ Timeout esperando QA para PR #{pr_number}")
        self.container_manager.destroy_container(task_id)

    def approve(
        self,
        pr_number: int,
        message: str,
        qa_agent: str,
        task_id: str,
    ):
        """QA approves the PR.

        Args:
            pr_number: PR number
            message: Approval message
            qa_agent: QA agent name
            task_id: Task ID
        """
        with self._lock:
            self._results[pr_number] = QAReviewResult(
                pr_number=pr_number,
                approved=True,
                message=message,
                reviewed_by=qa_agent,
                task_id=task_id,
            )

    def reject(
        self,
        pr_number: int,
        message: str,
        qa_agent: str,
        task_id: str,
    ):
        """QA rejects the PR.

        Args:
            pr_number: PR number
            message: Rejection reason
            qa_agent: QA agent name
            task_id: Task ID
        """
        with self._lock:
            self._results[pr_number] = QAReviewResult(
                pr_number=pr_number,
                approved=False,
                message=message,
                reviewed_by=qa_agent,
                task_id=task_id,
            )

    def _notify_human_for_merge(self, pr_number: int, result: QAReviewResult):
        """Notify human that PR is ready for merge."""

        notification = f"""
✅ **PR #{pr_number} Aprobado por QA**

**Revisado por:** {result.reviewed_by}
**Mensaje:** {result.message}

**Acción requerida:** Merge manual en GitHub

El PR ha pasado todos los quality gates y ha sido revisado por el agente de QA.
Está listo para merge a main.

**Para mergear:**
1. Ir al PR en GitHub
2. Verificar que todos los checks pasaron
3. Click en "Merge pull request"
4. Seleccionar "Create a merge commit" o "Squash and merge"
        """

        print(notification)
        # TODO: Send to Slack/email/Flux notification


class QAReviewStore:
    """Stores QA review history."""

    def __init__(self):
        self._reviews = {}

    def save_review(self, result: QAReviewResult):
        """Save a review result."""
        key = f"{result.pr_number}-{int(time.time())}"
        self._reviews[key] = result

    def get_review(self, pr_number: int) -> Optional[QAReviewResult]:
        """Get latest review for a PR."""
        # Find most recent review for this PR
        matching = [r for r in self._reviews.values() if r.pr_number == pr_number]
        return matching[-1] if matching else None

    def list_pending_reviews(self) -> list[int]:
        """List PRs pending review."""
        # This would query from monitored_prs
        return []
