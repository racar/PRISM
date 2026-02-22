"""Container Manager - Manages Docker test containers for PRISM.

Handles container lifecycle: create, start, monitor, destroy.
Enforces resource limits per role (architect: 1, dev: 2, test: 2).
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import docker


@dataclass
class TestContainer:
    """Represents a running test container."""

    id: str
    name: str
    task_id: str
    branch: str
    status: str  # creating, running, testing, ready_for_qa, approved, rejected
    web_terminal_url: Optional[str] = None
    role: str = "developer"  # architect, developer, test, optimizer


class ContainerManager:
    """Manages test containers with resource limits per role."""

    # Resource limits per role
    ROLE_LIMITS = {
        "architect": 1,
        "developer": 2,
        "test": 2,
        "optimizer": 5,  # Optimizers can run multiple
        "memory": 3,
    }

    def __init__(self):
        try:
            self.client = docker.from_env()
        except docker.errors.DockerException:
            raise RuntimeError(
                "Docker no está disponible. "
                "Asegúrate de que Docker esté instalado y corriendo."
            )

        self.network_name = "prism-test-network"
        self._ensure_network()

    def _ensure_network(self):
        """Ensure the test network exists."""
        try:
            self.client.networks.get(self.network_name)
        except docker.errors.NotFound:
            self.client.networks.create(
                self.network_name, driver="bridge", labels={"prism": "test-network"}
            )

    def launch_test_container(
        self, task_id: str, branch: str, role: str = "developer"
    ) -> TestContainer:
        """Launch a new test container.

        Args:
            task_id: The task ID for this container
            branch: Git branch to test
            role: Agent role (affects resource limits)

        Returns:
            TestContainer instance

        Raises:
            RuntimeError: If resource limits are exceeded
        """
        container_name = f"prism-test-{task_id}"

        # Check resource limits
        self._enforce_resource_limits(role)

        print(f"🐳 Creando contenedor: {container_name}")

        try:
            # Build docker command
            env_vars = {
                "TASK_ID": task_id,
                "GIT_BRANCH": branch,
                "GITHUB_TOKEN": self._get_github_token(),
                "GITHUB_REPO": self._get_github_repo(),
                "FLUX_WEBHOOK_URL": self._get_flux_webhook(),
                "PRISM_ROLE": role,
            }

            # Run container with docker-compose for better resource management
            compose_file = (
                Path(__file__).parent.parent / "docker" / "docker-compose.test.yml"
            )

            # Set environment for compose
            compose_env = {
                **env_vars,
                "CONTAINER_NAME": container_name,
            }

            # Use docker compose run
            cmd = [
                "docker",
                "compose",
                "-f",
                str(compose_file),
                "run",
                "-d",
                "--rm",
                "--name",
                container_name,
                "prism-test",
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                env={**subprocess.os.environ, **compose_env},
            )

            if result.returncode != 0:
                raise RuntimeError(f"Failed to start container: {result.stderr}")

            container_id = result.stdout.strip()

            # Get the actual container object
            container = self.client.containers.get(container_name)

            # Wait a moment for ttyd to start
            import time

            time.sleep(3)

            # Get the assigned port
            container.reload()
            ports = container.attrs["NetworkSettings"]["Ports"]

            web_url = None
            if ports and "7681/tcp" in ports and ports["7681/tcp"]:
                host_port = ports["7681/tcp"][0]["HostPort"]
                web_url = f"http://localhost:{host_port}"

            return TestContainer(
                id=container.id,
                name=container_name,
                task_id=task_id,
                branch=branch,
                status="creating",
                web_terminal_url=web_url,
                role=role,
            )

        except Exception as e:
            raise RuntimeError(f"Failed to create container: {e}")

    def _enforce_resource_limits(self, role: str):
        """Check and enforce resource limits per role."""
        limit = self.ROLE_LIMITS.get(role, 2)

        # Count running containers by role
        containers = self.client.containers.list(
            filters={"label": "prism.test.task"}, all=False
        )

        role_count = sum(
            1 for c in containers if c.labels.get("prism.test.role") == role
        )

        if role_count >= limit:
            raise RuntimeError(
                f"Límite de contenedores de {role} alcanzado (max {limit}). "
                f"Espera a que termine uno existente."
            )

    def _get_github_token(self) -> str:
        """Get GitHub token from environment."""
        import os

        token = os.environ.get("GITHUB_TOKEN")
        if not token:
            raise RuntimeError("GITHUB_TOKEN no está configurado")
        return token

    def _get_github_repo(self) -> str:
        """Get GitHub repo from environment."""
        import os

        return os.environ.get("GITHUB_REPO", "user/repo")

    def _get_flux_webhook(self) -> str:
        """Get Flux webhook URL from environment."""
        import os

        return os.environ.get("FLUX_WEBHOOK_URL", "")

    def get_container_status(self, task_id: str) -> Optional[TestContainer]:
        """Get status of a test container.

        Args:
            task_id: The task ID

        Returns:
            TestContainer or None if not found
        """
        try:
            container_name = f"prism-test-{task_id}"
            container = self.client.containers.get(container_name)

            # Get web terminal URL
            container.reload()
            ports = container.attrs["NetworkSettings"]["Ports"]

            web_url = None
            if ports and "7681/tcp" in ports and ports["7681/tcp"]:
                host_port = ports["7681/tcp"][0]["HostPort"]
                web_url = f"http://localhost:{host_port}"

            # Check actual status from file if available
            status = container.labels.get("prism.test.status", "unknown")

            # Try to get status from container filesystem
            try:
                exit_code, output = container.exec_run("cat /tmp/prism_status")
                if exit_code == 0:
                    status = output.decode().strip()
            except:
                pass

            return TestContainer(
                id=container.id,
                name=container.name,
                task_id=task_id,
                branch=container.labels.get("prism.test.branch", "unknown"),
                status=status,
                web_terminal_url=web_url,
                role=container.labels.get("prism.test.role", "developer"),
            )

        except docker.errors.NotFound:
            return None

    def destroy_container(self, task_id: str):
        """Destroy a test container.

        Args:
            task_id: The task ID
        """
        try:
            container_name = f"prism-test-{task_id}"
            container = self.client.containers.get(container_name)

            print(f"🗑️  Destruyendo contenedor: {container.name}")

            # Stop and remove
            container.stop(timeout=10)
            container.remove(force=True)

            print(f"✅ Contenedor {task_id} destruido")

        except docker.errors.NotFound:
            print(f"⚠️  Contenedor {task_id} no encontrado")

    def list_active_containers(self) -> list[TestContainer]:
        """List all active test containers.

        Returns:
            List of TestContainer instances
        """
        try:
            containers = self.client.containers.list(
                filters={"label": "prism.test.task"}, all=False
            )

            result = []
            for container in containers:
                task_id = container.labels.get("prism.test.task", "unknown")
                status = self.get_container_status(task_id)
                if status:
                    result.append(status)

            return result

        except Exception as e:
            print(f"Error listando contenedores: {e}")
            return []

    def execute_in_container(self, task_id: str, command: str) -> tuple[int, str, str]:
        """Execute a command in a container.

        Args:
            task_id: The task ID
            command: Command to execute

        Returns:
            Tuple of (exit_code, stdout, stderr)
        """
        try:
            container_name = f"prism-test-{task_id}"
            container = self.client.containers.get(container_name)

            exit_code, output = container.exec_run(
                ["/bin/bash", "-c", command], workdir="/app"
            )

            output_str = output.decode() if output else ""

            return exit_code, output_str, ""

        except docker.errors.NotFound:
            return 1, "", f"Contenedor {task_id} no encontrado"

        except Exception as e:
            return 1, "", str(e)

    def wait_for_ready(
        self, task_id: str, timeout: int = 600, poll_interval: int = 5
    ) -> bool:
        """Wait for a container to be ready for QA.

        Args:
            task_id: The task ID
            timeout: Maximum time to wait in seconds
            poll_interval: Seconds between checks

        Returns:
            True if ready, False if timeout or error
        """
        import time

        start = time.time()

        while time.time() - start < timeout:
            status = self.get_container_status(task_id)

            if not status:
                return False  # Container died

            if status.status == "ready_for_qa":
                return True

            if status.status == "failed":
                return False

            time.sleep(poll_interval)

        return False  # Timeout
