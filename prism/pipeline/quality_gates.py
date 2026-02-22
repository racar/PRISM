"""Quality Gates - Sequential fail-fast testing pipeline for PRISM.

This module executes quality checks in sequence, failing immediately
when any gate doesn't pass to provide fast feedback.
"""

from __future__ import annotations

import subprocess
import sys
import time
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class GateResult:
    """Result of a single quality gate execution."""

    name: str
    passed: bool
    duration_ms: int
    output: str
    error_output: Optional[str] = None
    command: str = field(default="")


@dataclass
class QualityReport:
    """Complete report of all quality gates."""

    task_id: str
    all_passed: bool
    gates: list[GateResult]
    total_duration_ms: int
    failed_gate: Optional[str] = None


class QualityGatesRunner:
    """Executes quality gates in fail-fast sequence.

    Sequence (fail fast):
    1. Linting (ruff) - 30s timeout
    2. Type Checking (mypy) - 60s timeout
    3. Unit Tests (pytest) - 120s timeout
    4. Coverage (>= 80%) - 120s timeout
    5. Integration Tests - 180s timeout
    """

    GATES = [
        {
            "name": "linting",
            "command": ["ruff", "check", "."],
            "timeout": 30,
            "description": "Linting with Ruff",
        },
        {
            "name": "type_checking",
            "command": ["mypy", "prism/", "--ignore-missing-imports"],
            "timeout": 60,
            "description": "Type checking with mypy",
        },
        {
            "name": "unit_tests",
            "command": ["pytest", "tests/unit", "-v", "--tb=short"],
            "timeout": 120,
            "description": "Unit tests",
        },
        {
            "name": "coverage",
            "command": [
                "pytest",
                "--cov=prism",
                "--cov-report=term-missing",
                "--cov-fail-under=80",
            ],
            "timeout": 120,
            "description": "Test coverage (min 80%)",
        },
        {
            "name": "integration_tests",
            "command": ["pytest", "tests/integration", "-v"],
            "timeout": 180,
            "description": "Integration tests",
        },
    ]

    def run_all(self, task_id: str) -> QualityReport:
        """Execute all gates in sequence.

        Args:
            task_id: The task being tested

        Returns:
            QualityReport with all results
        """
        results = []
        start_time = time.time()

        print("\n" + "=" * 70)
        print(f"🔍 PRISM Quality Gates - Task: {task_id}")
        print("=" * 70)
        print("Fail-fast mode enabled: Stops at first failure\n")

        for i, gate_config in enumerate(self.GATES, 1):
            print(f"\n[{i}/{len(self.GATES)}] {gate_config['description']}")
            print("-" * 70)

            result = self._run_gate(gate_config)
            results.append(result)

            # Print result
            status = "✅ PASS" if result.passed else "❌ FAIL"
            duration_sec = result.duration_ms / 1000
            print(f"{status} ({duration_sec:.1f}s)")

            if not result.passed:
                print(f"\n❌ GATE FAILED: {gate_config['name']}")
                print("Pipeline stopped. Fix this issue before continuing.\n")

                total_duration = int((time.time() - start_time) * 1000)
                return QualityReport(
                    task_id=task_id,
                    all_passed=False,
                    gates=results,
                    total_duration_ms=total_duration,
                    failed_gate=gate_config["name"],
                )

        # All gates passed
        total_duration = int((time.time() - start_time) * 1000)

        print("\n" + "=" * 70)
        print(f"✅ ALL GATES PASSED ({len(results)}/{len(results)})")
        print(f"Total time: {total_duration / 1000:.1f}s")
        print("=" * 70 + "\n")

        return QualityReport(
            task_id=task_id,
            all_passed=True,
            gates=results,
            total_duration_ms=total_duration,
        )

    def _run_gate(self, config: dict) -> GateResult:
        """Execute a single quality gate.

        Args:
            config: Gate configuration dict

        Returns:
            GateResult with execution details
        """
        start_time = time.time()
        cmd_str = " ".join(config["command"])

        try:
            result = subprocess.run(
                config["command"],
                capture_output=True,
                text=True,
                timeout=config["timeout"],
            )

            duration_ms = int((time.time() - start_time) * 1000)

            # Print output for visibility
            if result.stdout:
                # Limit output length
                output = result.stdout[:2000]
                if len(result.stdout) > 2000:
                    output += "\n... (output truncated)"
                print(output)

            return GateResult(
                name=config["name"],
                passed=result.returncode == 0,
                duration_ms=duration_ms,
                output=result.stdout,
                error_output=result.stderr if result.returncode != 0 else None,
                command=cmd_str,
            )

        except subprocess.TimeoutExpired as e:
            duration_ms = int(config["timeout"] * 1000)
            error_msg = f"Timeout after {config['timeout']}s"
            print(f"⏰ {error_msg}")

            return GateResult(
                name=config["name"],
                passed=False,
                duration_ms=duration_ms,
                output=e.stdout if e.stdout else "",
                error_output=error_msg,
                command=cmd_str,
            )

        except FileNotFoundError as e:
            duration_ms = int((time.time() - start_time) * 1000)
            error_msg = f"Command not found: {config['command'][0]}"
            print(f"❌ {error_msg}")

            return GateResult(
                name=config["name"],
                passed=False,
                duration_ms=duration_ms,
                output="",
                error_output=error_msg,
                command=cmd_str,
            )

    def run_single(self, gate_name: str) -> GateResult:
        """Run a single gate by name.

        Args:
            gate_name: Name of the gate to run

        Returns:
            GateResult
        """
        gate = next((g for g in self.GATES if g["name"] == gate_name), None)
        if not gate:
            raise ValueError(f"Unknown gate: {gate_name}")

        return self._run_gate(gate)


def format_report(report: QualityReport) -> str:
    """Format a quality report for display.

    Args:
        report: The quality report to format

    Returns:
        Formatted string
    """
    lines = []
    lines.append("\n" + "=" * 70)
    lines.append(f"Quality Report - Task: {report.task_id}")
    lines.append("=" * 70)

    for gate in report.gates:
        status = "✅" if gate.passed else "❌"
        duration_sec = gate.duration_ms / 1000
        lines.append(f"{status} {gate.name:20s} ({duration_sec:5.1f}s)")

    lines.append("-" * 70)

    if report.all_passed:
        lines.append(f"✅ ALL PASSED ({len(report.gates)}/{len(report.gates)} gates)")
    else:
        lines.append(f"❌ FAILED at: {report.failed_gate}")

    total_sec = report.total_duration_ms / 1000
    lines.append(f"Total time: {total_sec:.1f}s")
    lines.append("=" * 70)

    return "\n".join(lines)


def main():
    """CLI entrypoint."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Run PRISM quality gates",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m prism.pipeline.quality_gates run --task-id TASK-42
  python -m prism.pipeline.quality_gates run --task-id TASK-42 --verbose
  python -m prism.pipeline.quality_gates single --gate linting
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Run all gates
    run_parser = subparsers.add_parser("run", help="Run all quality gates")
    run_parser.add_argument(
        "--task-id",
        required=True,
        help="Task ID for reporting",
    )
    run_parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Verbose output",
    )

    # Run single gate
    single_parser = subparsers.add_parser("single", help="Run a single gate")
    single_parser.add_argument(
        "--gate",
        required=True,
        choices=[g["name"] for g in QualityGatesRunner.GATES],
        help="Gate to run",
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    runner = QualityGatesRunner()

    if args.command == "run":
        report = runner.run_all(args.task_id)

        if args.verbose:
            print(format_report(report))

        # Exit with error code if any gate failed
        sys.exit(0 if report.all_passed else 1)

    elif args.command == "single":
        result = runner.run_single(args.gate)

        print(f"\n{'✅ PASS' if result.passed else '❌ FAIL'}: {result.name}")
        if result.output:
            print(f"\nOutput:\n{result.output[:1000]}")
        if result.error_output:
            print(f"\nError:\n{result.error_output}")

        sys.exit(0 if result.passed else 1)


if __name__ == "__main__":
    main()
