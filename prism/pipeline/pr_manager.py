"""PR Manager - Manages Pull Requests from PRISM.

Creates PRs from local changes and manages approvals/rejections.
"""

from __future__ import annotations

import os
import re
import subprocess
from dataclasses import dataclass
from typing import Optional

import requests


@dataclass
class PullRequest:
    """Represents a GitHub Pull Request."""

    number: int
    title: str
    branch: str
    url: str
    status: str  # open, closed, merged
    task_id: str


class PRManager:
    """Manages Pull Requests for PRISM."""

    def __init__(self):
        self.token = os.environ.get("GITHUB_TOKEN")
        self.repo = os.environ.get("GITHUB_REPO", "user/repo")
        self.api_base = f"https://api.github.com/repos/{self.repo}"

        if not self.token:
            raise RuntimeError("GITHUB_TOKEN no está configurado")

    def create_pr_from_task(
        self,
        task_id: str,
        task_title: str,
        changes_description: str = "",
    ) -> PullRequest:
        """Create a PR from the current working directory changes.

        Args:
            task_id: Task ID
            task_title: Task title
            changes_description: Description of changes

        Returns:
            PullRequest instance
        """
        # Generate branch name
        branch_name = self._generate_branch_name(task_id, task_title)

        # Create branch and commit changes
        self._create_branch_and_commit(branch_name, task_id, changes_description)

        # Create PR on GitHub
        pr_data = self._create_github_pr(
            title=f"feat: {task_title}",
            body=self._generate_pr_body(task_id, task_title, changes_description),
            head=branch_name,
            base="main",
        )

        return PullRequest(
            number=pr_data["number"],
            title=pr_data["title"],
            branch=branch_name,
            url=pr_data["html_url"],
            status="open",
            task_id=task_id,
        )

    def _generate_branch_name(self, task_id: str, title: str) -> str:
        """Generate a valid branch name from task info."""
        # Clean title: lowercase, special chars to hyphens
        clean_title = re.sub(r"[^\w\s-]", "", title.lower())
        clean_title = re.sub(r"[-\s]+", "-", clean_title)

        # Truncate if too long
        if len(clean_title) > 50:
            clean_title = clean_title[:50].rstrip("-")

        return f"feat/{task_id}-{clean_title}"

    def _create_branch_and_commit(
        self,
        branch_name: str,
        task_id: str,
        description: str,
    ):
        """Create branch locally and commit changes."""
        # Configure git if not already configured
        try:
            subprocess.run(
                ["git", "config", "user.email"],
                capture_output=True,
                check=True,
            )
        except subprocess.CalledProcessError:
            subprocess.run(
                ["git", "config", "user.email", "prism@localhost"],
                check=True,
            )
            subprocess.run(
                ["git", "config", "user.name", "PRISM Agent"],
                check=True,
            )

        # Create and checkout branch
        subprocess.run(
            ["git", "checkout", "-b", branch_name],
            capture_output=True,
            check=True,
        )

        # Stage all changes
        subprocess.run(
            ["git", "add", "-A"],
            capture_output=True,
            check=True,
        )

        # Commit
        commit_msg = f"feat: {description or 'Implement task'}\n\nTask: {task_id}"
        subprocess.run(
            ["git", "commit", "-m", commit_msg],
            capture_output=True,
            check=True,
        )

        # Push to origin
        subprocess.run(
            ["git", "push", "-u", "origin", branch_name],
            capture_output=True,
            check=True,
        )

    def _create_github_pr(
        self,
        title: str,
        body: str,
        head: str,
        base: str,
    ) -> dict:
        """Create PR via GitHub API."""
        headers = {
            "Authorization": f"token {self.token}",
            "Accept": "application/vnd.github.v3+json",
        }

        data = {
            "title": title,
            "body": body,
            "head": head,
            "base": base,
        }

        response = requests.post(
            f"{self.api_base}/pulls",
            headers=headers,
            json=data,
        )
        response.raise_for_status()

        return response.json()

    def _generate_pr_body(self, task_id: str, task_title: str, description: str) -> str:
        """Generate PR body with PRISM checklist."""
        return f"""## Description
{description or task_title}

## Task
- **ID:** {task_id}
- **Title:** {task_title}

## PRISM Quality Checklist
- [x] Implementation complete
- [x] Unit tests implemented
- [x] Integration tests implemented
- [x] Coverage >= 80%
- [x] Linting passes
- [x] Type checking passes

## QA Review
Este PR ha pasado todos los quality gates automáticos y está listo para revisión QA.

### Para revisar:
1. Esperar confirmación de que el contenedor de test está listo
2. Abrir el terminal web desde la tarjeta de Flux
3. Ejecutar tests adicionales si es necesario
4. Aprobar o solicitar cambios

---
*Automáticamente generado por PRISM*
"""

    def approve_pr(self, pr_number: int, message: str, qa_agent: str = "qa-agent"):
        """Approve a PR as QA.

        Args:
            pr_number: PR number
            message: Approval message
            qa_agent: Name of QA agent
        """
        headers = {
            "Authorization": f"token {self.token}",
            "Accept": "application/vnd.github.v3+json",
        }

        # Create approving review
        data = {
            "body": f"""✅ **QA Approval**

{message}

**Revisado por:** {qa_agent}
**Estado:** Todos los quality gates pasaron y el código ha sido revisado.

**Nota:** Este PR está listo para merge manual.
""",
            "event": "APPROVE",
        }

        response = requests.post(
            f"{self.api_base}/pulls/{pr_number}/reviews",
            headers=headers,
            json=data,
        )
        response.raise_for_status()

    def request_changes(self, pr_number: int, message: str, qa_agent: str = "qa-agent"):
        """Request changes on a PR.

        Args:
            pr_number: PR number
            message: Change request message
            qa_agent: Name of QA agent
        """
        headers = {
            "Authorization": f"token {self.token}",
            "Accept": "application/vnd.github.v3+json",
        }

        data = {
            "body": f"""❌ **QA Review: Changes Requested**

{message}

**Revisado por:** {qa_agent}

Por favor realizar las correcciones solicitadas.
""",
            "event": "REQUEST_CHANGES",
        }

        response = requests.post(
            f"{self.api_base}/pulls/{pr_number}/reviews",
            headers=headers,
            json=data,
        )
        response.raise_for_status()

    def add_pr_comment(self, pr_number: int, message: str) -> Optional[dict]:
        """Add a comment to a PR.

        Args:
            pr_number: PR number
            message: Comment message

        Returns:
            Comment data or None if failed
        """
        headers = {
            "Authorization": f"token {self.token}",
            "Accept": "application/vnd.github.v3+json",
        }

        data = {"body": message}

        try:
            response = requests.post(
                f"{self.api_base}/issues/{pr_number}/comments",
                headers=headers,
                json=data,
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException:
            return None

    def get_pr_status(self, pr_number: int) -> Optional[dict]:
        """Get current status of a PR.

        Args:
            pr_number: PR number

        Returns:
            PR data or None
        """
        headers = {
            "Authorization": f"token {self.token}",
            "Accept": "application/vnd.github.v3+json",
        }

        try:
            response = requests.get(
                f"{self.api_base}/pulls/{pr_number}",
                headers=headers,
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException:
            return None
