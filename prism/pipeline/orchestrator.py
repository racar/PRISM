"""Pipeline Orchestrator - Coordinates the complete test automation flow.

Flow: Webhook → PR → Container → Quality Gates → QA Notify
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Optional

from prism.board.flux_client import FluxClient
from prism.pipeline.container_manager import ContainerManager, TestContainer
from prism.pipeline.pr_manager import PRManager, PullRequest
from prism.pipeline.quality_gates import QualityGatesRunner, QualityReport


@dataclass
class PipelineResult:
    """Result of a pipeline execution."""

    success: bool
    pr: Optional[PullRequest]
    container: Optional[TestContainer]
    report: Optional[QualityReport]
    message: str


class PipelineOrchestrator:
    """Coordinates the PRISM test automation pipeline."""

    def __init__(self):
        self.flux = FluxClient()
        self.pr_manager = PRManager()
        self.container_manager = ContainerManager()
        self.gates_runner = QualityGatesRunner()

    def process_task_done(self, task_id: str) -> PipelineResult:
        """Process a task moved to Done in Flux.

        Args:
            task_id: The task ID to process

        Returns:
            PipelineResult with execution details
        """
        print(f"🚀 Iniciando pipeline para task: {task_id}")

        # 1. Get task details
        try:
            task = self.flux.get_task(task_id)
            if not task:
                return PipelineResult(
                    success=False,
                    pr=None,
                    container=None,
                    report=None,
                    message=f"Task {task_id} no encontrado",
                )
        except Exception as e:
            return PipelineResult(
                success=False,
                pr=None,
                container=None,
                report=None,
                message=f"Error obteniendo task: {e}",
            )

        # 2. Create PR
        print("📦 Creando Pull Request...")
        try:
            pr = self.pr_manager.create_pr_from_task(
                task_id=task_id,
                task_title=task.title,
                changes_description=task.body or "",
            )
            print(f"✅ PR creado: #{pr.number} - {pr.url}")
        except Exception as e:
            return PipelineResult(
                success=False,
                pr=None,
                container=None,
                report=None,
                message=f"Error creando PR: {e}",
            )

        # 3. Launch test container
        print("🐳 Lanzando contenedor de prueba...")
        try:
            container = self.container_manager.launch_test_container(
                task_id=task_id,
                branch=pr.branch,
                role=task.assigned_role or "developer",
            )
            print(f"✅ Contenedor listo: {container.name}")
            print(f"🖥️  Terminal: {container.web_terminal_url}")
        except Exception as e:
            # Rollback PR if container fails
            print(f"❌ Error lanzando contenedor: {e}")
            return PipelineResult(
                success=False,
                pr=pr,
                container=None,
                report=None,
                message=f"Error lanzando contenedor: {e}",
            )

        # 4. Update Flux task with container info
        try:
            self.flux.update_task(
                task_id=task_id,
                notes=f"""
**PRISM Pipeline Iniciado**

🐳 Contenedor: `{container.name}`
🖥️ Terminal: [Abrir]({container.web_terminal_url})
🔗 PR: [#{pr.number}]({pr.url})

Estado: ⏳ Ejecutando quality gates...
                """,
            )
        except Exception as e:
            print(f"⚠️  No se pudo actualizar Flux: {e}")

        # 5. Wait for container to finish quality gates
        print("⏳ Esperando quality gates en contenedor...")
        success = self.container_manager.wait_for_ready(
            task_id=task_id,
            timeout=600,
            poll_interval=5,
        )

        if not success:
            # Quality gates failed
            print("❌ Quality gates fallaron")

            # Update Flux
            try:
                self.flux.update_task(
                    task_id=task_id,
                    status="Backlog",
                    notes=f"""
❌ **Quality Gates FAILED**

Revisar logs en contenedor:
`docker logs {container.name}`

🔗 PR: #{pr.number}
                    """,
                )
            except Exception as e:
                print(f"⚠️  No se pudo actualizar Flux: {e}")

            return PipelineResult(
                success=False,
                pr=pr,
                container=container,
                report=None,
                message="Quality gates failed",
            )

        # 6. Quality gates passed
        print("✅ Quality gates pasaron. Notificando QA...")

        # Get updated container status
        container = self.container_manager.get_container_status(task_id)

        # Update Flux to Ready for QA
        try:
            self.flux.update_task(
                task_id=task_id,
                status="Review",
                notes=f"""
✅ **Quality Gates PASSED - Ready for QA**

📊 Results:
• Linting: ✅
• Type Checking: ✅
• Unit Tests: ✅
• Coverage: >= 80% ✅
• Integration Tests: ✅

🐳 Contenedor: `{container.name}`
🖥️ Terminal: [Revisar]({container.web_terminal_url})
🔗 PR: [#{pr.number}]({pr.url})

**Acciones QA:**
1. Click en Web Terminal para revisar
2. Ejecutar: `prism approve --pr {pr.number}` para aprobar
3. Ejecutar: `prism reject --pr {pr.number}` para rechazar
                """,
            )
        except Exception as e:
            print(f"⚠️  No se pudo actualizar Flux: {e}")

        return PipelineResult(
            success=True,
            pr=pr,
            container=container,
            report=None,  # Report is inside container
            message="Ready for QA review",
        )

    def submit_for_qa_manual(self, task_id: str, message: str = "") -> PipelineResult:
        """Manual submission for QA (alternative to webhook).

        Args:
            task_id: Task ID
            message: Optional description

        Returns:
            PipelineResult
        """
        print(f"🚀 Enviando manualmente task {task_id} a QA...")
        return self.process_task_done(task_id)

    def get_pipeline_status(self, task_id: str) -> dict:
        """Get current status of a pipeline.

        Args:
            task_id: Task ID

        Returns:
            Status dictionary
        """
        container = self.container_manager.get_container_status(task_id)

        if not container:
            return {
                "task_id": task_id,
                "status": "unknown",
                "message": "No container found",
            }

        return {
            "task_id": task_id,
            "status": container.status,
            "container": container.name,
            "web_terminal": container.web_terminal_url,
            "branch": container.branch,
            "role": container.role,
        }
