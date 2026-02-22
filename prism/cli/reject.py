"""Reject - QA rejects a PR."""

import click

from prism.pipeline.pr_manager import PRManager
from prism.qa.approval_workflow import QAApprovalWorkflow


@click.command(name="reject")
@click.option("--pr", type=int, help="Número del PR")
@click.option("--task-id", help="ID del task (alternativa a --pr)")
@click.option("--reason", required=True, help="Razón del rechazo")
@click.option("--qa-agent", default="qa-agent", help="Nombre del QA agent")
def reject_pr(pr: int, task_id: str, reason: str, qa_agent: str):
    """Rechaza un PR como QA.

    Ejemplos:
        prism reject --pr 123 --reason "Falta manejo de errores"
        prism reject --task TASK-42 --reason "Cobertura solo 60%"
    """

    if task_id and not pr:
        click.echo(f"🔍 Buscando PR para task {task_id}...")
        raise click.ClickException("Usa --pr con el número del PR directamente")

    if not pr:
        raise click.ClickException("--pr es requerido")

    click.echo(f"❌ Rechazando PR #{pr}...")

    # Rechazar en el workflow
    workflow = QAApprovalWorkflow()
    workflow.reject(pr, reason, qa_agent, task_id or "unknown")

    # Solicitar cambios en GitHub
    try:
        pr_manager = PRManager()
        pr_manager.request_changes(pr, reason, qa_agent)
        click.echo(f"❌ PR #{pr} marcado como 'changes requested' en GitHub")
    except Exception as e:
        click.echo(f"⚠️  Error en GitHub: {e}")

    click.echo("")
    click.echo(f"📝 Razón: {reason}")
    click.echo("🔧 Developer será notificado para corregir")
    click.echo("   El contenedor se mantendrá por 30 min para debugging")
