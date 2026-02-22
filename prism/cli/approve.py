"""Approve - QA approves a PR."""

import click

from prism.pipeline.pr_manager import PRManager
from prism.qa.approval_workflow import QAApprovalWorkflow


@click.command(name="approve")
@click.option("--pr", type=int, help="Número del PR")
@click.option("--task-id", help="ID del task (alternativa a --pr)")
@click.option("--message", default="Code review passed", help="Mensaje de aprobación")
@click.option("--qa-agent", default="qa-agent", help="Nombre del QA agent")
def approve_pr(pr: int, task_id: str, message: str, qa_agent: str):
    """Aprueba un PR como QA.

    Ejemplos:
        prism approve --pr 123
        prism approve --task TASK-42 --message "Excelente implementación"
    """

    # Si tenemos task_id pero no pr, necesitamos obtener el PR number
    if task_id and not pr:
        # Buscar PR asociado al task
        click.echo(f"🔍 Buscando PR para task {task_id}...")
        # Esto requeriría almacenar la relación task->pr
        raise click.ClickException("Usa --pr con el número del PR directamente")

    if not pr:
        raise click.ClickException("--pr es requerido")

    click.echo(f"✅ Aprobando PR #{pr}...")

    # Aprobar en el workflow
    workflow = QAApprovalWorkflow()
    workflow.approve(pr, message, qa_agent, task_id or "unknown")

    # Aprobar en GitHub
    try:
        pr_manager = PRManager()
        pr_manager.approve_pr(pr, message, qa_agent)
        click.echo(f"✅ PR #{pr} aprobado en GitHub")
    except Exception as e:
        click.echo(f"⚠️  Error aprobando en GitHub: {e}")

    click.echo("")
    click.echo("📝 Notificación enviada al humano para merge manual")
    click.echo("   El PR está listo para merge en GitHub")
