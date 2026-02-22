"""Container Access - Provides access to test containers for QA agents.

Integrates web terminal with Flux for interactive review.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass


@dataclass
class ContainerSession:
    """Represents a session to access a test container."""

    task_id: str
    container_name: str
    web_terminal_url: str
    shell_command: str


class ContainerAccess:
    """Manages access to test containers for QA review."""

    def get_session(self, task_id: str) -> ContainerSession:
        """Get access session for a container.

        Args:
            task_id: The task ID

        Returns:
            ContainerSession with connection details
        """
        container_name = f"prism-test-{task_id}"

        # Get web terminal port
        result = subprocess.run(
            ["docker", "port", container_name, "7681"],
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            raise RuntimeError(f"Contenedor no encontrado: {container_name}")

        # Parse port
        port_info = result.stdout.strip()
        host_port = port_info.split(":")[-1]

        web_url = f"http://localhost:{host_port}"

        # Local shell command
        shell_cmd = f"docker exec -it {container_name} /bin/bash"

        return ContainerSession(
            task_id=task_id,
            container_name=container_name,
            web_terminal_url=web_url,
            shell_command=shell_cmd,
        )

    def execute_in_container(
        self,
        task_id: str,
        command: str,
    ) -> tuple[int, str, str]:
        """Execute a command in the container.

        Args:
            task_id: Task ID
            command: Command to execute

        Returns:
            Tuple of (exit_code, stdout, stderr)
        """
        container_name = f"prism-test-{task_id}"

        result = subprocess.run(
            ["docker", "exec", container_name, "/bin/bash", "-c", command],
            capture_output=True,
            text=True,
        )

        return result.returncode, result.stdout, result.stderr

    def check_status(self, task_id: str) -> str:
        """Check QA decision status in container.

        Args:
            task_id: Task ID

        Returns:
            Status: pending, approved, rejected, or unknown
        """
        try:
            exit_code, output, _ = self.execute_in_container(
                task_id, "cat /tmp/qa_decision 2>/dev/null || echo 'pending'"
            )

            if exit_code == 0:
                status = output.strip()
                return status if status in ["approved", "rejected"] else "pending"

            return "unknown"

        except Exception:
            return "unknown"


class FluxTerminalIntegration:
    """Integrates web terminal with Flux task cards."""

    def __init__(self):
        self.container_access = ContainerAccess()

    def add_terminal_to_task_card(self, task_id: str, pr_number: int) -> dict:
        """Generate Flux task card update with terminal link.

        Args:
            task_id: Task ID
            pr_number: PR number

        Returns:
            Flux update payload
        """
        try:
            session = self.container_access.get_session(task_id)

            return {
                "task_id": task_id,
                "custom_fields": {
                    "test_terminal_url": session.web_terminal_url,
                    "test_container": session.container_name,
                    "pr_number": pr_number,
                },
                "actions": [
                    {
                        "type": "button",
                        "label": "🖥️ Open Test Terminal",
                        "url": session.web_terminal_url,
                        "description": "Abre terminal web en el contenedor de pruebas",
                    },
                    {
                        "type": "button",
                        "label": "✅ Approve PR",
                        "command": f"prism approve --pr {pr_number}",
                    },
                    {
                        "type": "button",
                        "label": "❌ Request Changes",
                        "command": f"prism reject --pr {pr_number}",
                    },
                ],
            }

        except Exception as e:
            return {
                "task_id": task_id,
                "error": str(e),
            }
