"""Review - QA reviews a test container."""

import click
import subprocess

from prism.qa.container_access import ContainerAccess


@click.command(name="review")
@click.option("--task-id", help="ID del task a revisar")
@click.option("--container", help="Nombre del contenedor (alternativa a task-id)")
@click.option("--command", help="Comando a ejecutar en el contenedor")
def review(task_id: str, container: str, command: str):
    """Revisa un contenedor de prueba como QA.

    Ejemplos:
        prism review --task TASK-42
        prism review --container prism-test-TASK-42
        prism review --task TASK-42 --command "pytest tests/ -v"
    """

    access = ContainerAccess()

    # Determinar task_id
    if not task_id and not container:
        raise click.ClickException("--task-id o --container requerido")

    if container and not task_id:
        # Extraer task_id del nombre del contenedor
        task_id = container.replace("prism-test-", "")

    try:
        session = access.get_session(task_id)
    except RuntimeError as e:
        raise click.ClickException(str(e))

    if command:
        # Ejecutar comando y mostrar resultado
        click.echo(f"🐳 Contenedor: {session.container_name}")
        click.echo(f"💻 Ejecutando: {command}")
        click.echo("-" * 70)

        exit_code, stdout, stderr = access.execute_in_container(task_id, command)

        if stdout:
            click.echo(stdout)
        if stderr:
            click.echo(stderr, err=True)

        click.echo("-" * 70)
        click.echo(f"Exit code: {exit_code}")

    else:
        # Mostrar información de conexión
        click.echo(f"🐳 Contenedor: {session.container_name}")
        click.echo(f"🔗 Task ID: {session.task_id}")
        click.echo("")
        click.echo(f"🖥️  Web Terminal: {session.web_terminal_url}")
        click.echo(f"💻 Shell local: {session.shell_command}")
        click.echo("")
        click.echo("Comandos útiles para revisar:")
        click.echo(f"  prism review --task {task_id} --command 'pytest tests/ -v'")
        click.echo(f"  prism review --task {task_id} --command 'cat src/main.py'")
        click.echo(f"  prism review --task {task_id} --command 'git diff main...HEAD'")
        click.echo("")
        click.echo("Para aprobar/rechazar:")
        click.echo(f"  prism approve --pr <numero_pr> --message 'LGTM'")
        click.echo(f"  prism reject --pr <numero_pr> --reason 'Falta documentación'")
