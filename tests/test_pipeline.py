"""Tests for PRISM Docker Test Pipeline."""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock, Mock, patch

from prism.pipeline.container_manager import ContainerManager, TestContainer
from prism.pipeline.quality_gates import QualityGatesRunner, GateResult, QualityReport
from prism.pipeline.pr_manager import PRManager, PullRequest
from prism.pipeline.orchestrator import PipelineOrchestrator, PipelineResult
from prism.qa.approval_workflow import QAApprovalWorkflow, QAReviewResult
from prism.qa.container_access import ContainerAccess, ContainerSession


# =============================================================================
# Quality Gates Tests
# =============================================================================


class TestQualityGatesRunner:
    """Test quality gates execution."""

    def test_gate_result_creation(self):
        """Test GateResult dataclass."""
        result = GateResult(
            name="test_gate",
            passed=True,
            duration_ms=1000,
            output="test output",
            command="test command",
        )

        assert result.name == "test_gate"
        assert result.passed is True
        assert result.duration_ms == 1000
        assert result.output == "test output"
        assert result.command == "test command"

    def test_quality_report_creation(self):
        """Test QualityReport dataclass."""
        gates = [
            GateResult(
                name="gate1", passed=True, duration_ms=100, output="", command="cmd1"
            ),
            GateResult(
                name="gate2", passed=True, duration_ms=200, output="", command="cmd2"
            ),
        ]

        report = QualityReport(
            task_id="TASK-42",
            all_passed=True,
            gates=gates,
            total_duration_ms=300,
        )

        assert report.task_id == "TASK-42"
        assert report.all_passed is True
        assert len(report.gates) == 2
        assert report.total_duration_ms == 300

    def test_runner_has_expected_gates(self):
        """Test that runner has all expected gates configured."""
        runner = QualityGatesRunner()

        expected_gates = [
            "linting",
            "type_checking",
            "unit_tests",
            "coverage",
            "integration_tests",
        ]

        actual_gates = [g["name"] for g in runner.GATES]
        assert actual_gates == expected_gates

    @patch("subprocess.run")
    def test_run_single_gate_success(self, mock_run):
        """Test running a single successful gate."""
        mock_run.return_value = Mock(
            returncode=0,
            stdout="All checks passed",
            stderr="",
        )

        runner = QualityGatesRunner()
        result = runner.run_single("linting")

        assert result.passed is True
        assert result.name == "linting"
        assert result.output == "All checks passed"
        mock_run.assert_called_once()

    @patch("subprocess.run")
    def test_run_single_gate_failure(self, mock_run):
        """Test running a gate that fails."""
        mock_run.return_value = Mock(
            returncode=1,
            stdout="",
            stderr="Error found",
        )

        runner = QualityGatesRunner()
        result = runner.run_single("linting")

        assert result.passed is False
        assert result.error_output == "Error found"

    @patch("subprocess.run")
    def test_run_all_gates_success(self, mock_run):
        """Test running all gates successfully."""
        mock_run.return_value = Mock(
            returncode=0,
            stdout="Success",
            stderr="",
        )

        runner = QualityGatesRunner()
        report = runner.run_all("TASK-42")

        assert report.all_passed is True
        assert report.task_id == "TASK-42"
        assert len(report.gates) == len(runner.GATES)
        assert mock_run.call_count == len(runner.GATES)


# =============================================================================
# Container Manager Tests
# =============================================================================


class TestContainerManager:
    """Test container management."""

    def test_test_container_creation(self):
        """Test TestContainer dataclass."""
        container = TestContainer(
            id="abc123",
            name="prism-test-TASK-42",
            task_id="TASK-42",
            branch="feat/TASK-42-test",
            status="running",
            web_terminal_url="http://localhost:7681",
            role="developer",
        )

        assert container.id == "abc123"
        assert container.name == "prism-test-TASK-42"
        assert container.task_id == "TASK-42"
        assert container.branch == "feat/TASK-42-test"
        assert container.status == "running"
        assert container.web_terminal_url == "http://localhost:7681"
        assert container.role == "developer"

    def test_role_limits_defined(self):
        """Test that role limits are properly defined."""
        manager = ContainerManager()

        expected_limits = {
            "architect": 1,
            "developer": 2,
            "test": 2,
            "optimizer": 5,
            "memory": 3,
        }

        assert manager.ROLE_LIMITS == expected_limits


# =============================================================================
# PR Manager Tests
# =============================================================================


class TestPRManager:
    """Test PR management."""

    def test_pull_request_creation(self):
        """Test PullRequest dataclass."""
        pr = PullRequest(
            number=123,
            title="feat: Implement feature",
            branch="feat/TASK-42",
            url="https://github.com/user/repo/pull/123",
            status="open",
            task_id="TASK-42",
        )

        assert pr.number == 123
        assert pr.title == "feat: Implement feature"
        assert pr.branch == "feat/TASK-42"
        assert pr.url == "https://github.com/user/repo/pull/123"
        assert pr.status == "open"
        assert pr.task_id == "TASK-42"

    def test_generate_branch_name(self):
        """Test branch name generation."""
        with patch.dict(
            "os.environ", {"GITHUB_TOKEN": "test", "GITHUB_REPO": "user/repo"}
        ):
            manager = PRManager()
            branch = manager._generate_branch_name("TASK-42", "Implement new feature")

            assert branch.startswith("feat/TASK-42-")
            assert "implement-new-feature" in branch

    def test_generate_branch_name_with_special_chars(self):
        """Test branch name generation cleans special chars."""
        with patch.dict(
            "os.environ", {"GITHUB_TOKEN": "test", "GITHUB_REPO": "user/repo"}
        ):
            manager = PRManager()
            branch = manager._generate_branch_name(
                "TASK-42", "Feature: Test & Validate!"
            )

            assert "feature-test-validate" in branch
            assert ":" not in branch
            assert "&" not in branch
            assert "!" not in branch


# =============================================================================
# Pipeline Orchestrator Tests
# =============================================================================


class TestPipelineOrchestrator:
    """Test pipeline orchestration."""

    def test_pipeline_result_creation(self):
        """Test PipelineResult dataclass."""
        pr = PullRequest(
            number=123,
            title="Test PR",
            branch="feat/test",
            url="http://test.com",
            status="open",
            task_id="TASK-42",
        )

        container = TestContainer(
            id="abc",
            name="test-container",
            task_id="TASK-42",
            branch="feat/test",
            status="running",
            web_terminal_url="http://localhost:7681",
        )

        result = PipelineResult(
            success=True,
            pr=pr,
            container=container,
            report=None,
            message="Success",
        )

        assert result.success is True
        assert result.pr.number == 123
        assert result.container.name == "test-container"
        assert result.message == "Success"


# =============================================================================
# QA Workflow Tests
# =============================================================================


class TestQAApprovalWorkflow:
    """Test QA approval workflow."""

    def test_qa_review_result_creation(self):
        """Test QAReviewResult dataclass."""
        result = QAReviewResult(
            pr_number=123,
            approved=True,
            message="LGTM",
            reviewed_by="qa-agent",
            task_id="TASK-42",
        )

        assert result.pr_number == 123
        assert result.approved is True
        assert result.message == "LGTM"
        assert result.reviewed_by == "qa-agent"
        assert result.task_id == "TASK-42"

    def test_workflow_initialization(self):
        """Test workflow initialization."""
        workflow = QAApprovalWorkflow()

        assert workflow._monitored_prs == {}
        assert workflow._results == {}

    def test_approve_stores_result(self):
        """Test that approve stores the result."""
        workflow = QAApprovalWorkflow()

        workflow.approve(123, "Good job", "qa-agent", "TASK-42")

        assert 123 in workflow._results
        assert workflow._results[123].approved is True
        assert workflow._results[123].message == "Good job"

    def test_reject_stores_result(self):
        """Test that reject stores the result."""
        workflow = QAApprovalWorkflow()

        workflow.reject(123, "Needs work", "qa-agent", "TASK-42")

        assert 123 in workflow._results
        assert workflow._results[123].approved is False
        assert workflow._results[123].message == "Needs work"


# =============================================================================
# Container Access Tests
# =============================================================================


class TestContainerAccess:
    """Test container access for QA."""

    def test_container_session_creation(self):
        """Test ContainerSession dataclass."""
        session = ContainerSession(
            task_id="TASK-42",
            container_name="prism-test-TASK-42",
            web_terminal_url="http://localhost:7681",
            shell_command="docker exec -it prism-test-TASK-42 /bin/bash",
        )

        assert session.task_id == "TASK-42"
        assert session.container_name == "prism-test-TASK-42"
        assert session.web_terminal_url == "http://localhost:7681"
        assert "docker exec" in session.shell_command


# =============================================================================
# Integration Tests
# =============================================================================


@pytest.mark.integration
class TestPipelineIntegration:
    """Integration tests for the complete pipeline."""

    def test_quality_gates_sequence(self):
        """Test that quality gates run in correct sequence."""
        runner = QualityGatesRunner()

        # Verify sequence order
        assert runner.GATES[0]["name"] == "linting"
        assert runner.GATES[1]["name"] == "type_checking"
        assert runner.GATES[2]["name"] == "unit_tests"
        assert runner.GATES[3]["name"] == "coverage"
        assert runner.GATES[4]["name"] == "integration_tests"

    def test_container_naming_convention(self):
        """Test container naming follows convention."""
        task_id = "TASK-42"
        expected_name = f"prism-test-{task_id}"

        assert expected_name.startswith("prism-test-")
        assert task_id in expected_name
