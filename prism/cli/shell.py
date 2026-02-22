"""Shell - Opens interactive shell in test container."""

import subprocess

import click


@click.command(name="shell")
@click.option("--container", required=True, help="Nombre del contenedor")
@click.option("--task-id", help="ID del task (alternativa a --container)")
def shell(container: str, task_id: str):
    """Abre shell interactivo en un contenedor de prueba.

    Ejemplos:
        prism shell --container prism-test-TASK-42
        prism shell --task TASK-42
    """

    # Determinar nombre del contenedor
    if task_id and not container:
        container = f"prism-test-{task_id}"

    click.echo(f"🔌 Conectando a {container}...")
    click.echo("💡 Usa 'exit' para salir del contenedor")
    click.echo("")

    # Abrir shell interactivo
    subprocess.run(["docker", "exec", "-it", container, "/bin/bash"])
