from __future__ import annotations

import shutil
from datetime import date
from pathlib import Path

from rich.console import Console

from prism.config import GLOBAL_CONFIG_DIR, GLOBAL_CONFIG_PATH

console = Console()
TEMPLATES_DIR = Path(__file__).parent / "templates"


def check_docker() -> bool:
    return shutil.which("docker") is not None


def has_prism_spec(project_dir: Path) -> bool:
    return (project_dir / ".prism" / "spec" / "protocol" / "AGENT.md").exists()


def setup_prism_spec(project_dir: Path) -> None:
    protocol_dir = project_dir / ".prism" / "spec" / "protocol"
    protocol_dir.mkdir(parents=True, exist_ok=True)
    source = TEMPLATES_DIR / "spec-protocol" / "AGENT.md"
    dest = protocol_dir / "AGENT.md"
    shutil.copy(source, dest)
    console.print("[green]PRISM Spec protocol installed[/green]")


def create_prism_dir(project_dir: Path) -> Path:
    prism_dir = project_dir / ".prism"
    prism_dir.mkdir(parents=True, exist_ok=True)
    return prism_dir


def init_global_memory() -> Path:
    memory_dir = GLOBAL_CONFIG_DIR / "memory"
    for subdir in ["skills", "gotchas", "decisions", "episodes"]:
        (memory_dir / subdir).mkdir(parents=True, exist_ok=True)
    return memory_dir


def ensure_global_config() -> None:
    if not GLOBAL_CONFIG_PATH.exists():
        GLOBAL_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        shutil.copy(TEMPLATES_DIR / "prism.config.yaml.template", GLOBAL_CONFIG_PATH)


def render_template(name: str, ctx: dict) -> str:
    content = (TEMPLATES_DIR / name).read_text()
    for key, val in ctx.items():
        content = content.replace(f"{{{{ {key} }}}}", str(val))
    return content


def _write_template(dest: Path, template_name: str, ctx: dict) -> None:
    dest.write_text(render_template(template_name, ctx))


def _build_template_ctx(project_name: str, stack: list[str] | None = None) -> dict:
    return {
        "project_name": project_name,
        "date": str(date.today()),
        "stack": ", ".join(stack or []),
    }


def write_prism_files(
    prism_dir: Path, project_name: str, stack: list[str] | None = None
) -> None:
    ctx = _build_template_ctx(project_name, stack)
    _write_template(prism_dir / "PRISM.md", "PRISM.md.template", ctx)
    _write_template(prism_dir / "AGENTS.md", "AGENTS.md.template", ctx)
    _write_template(prism_dir / "project.yaml", "project.yaml.template", ctx)


def seed_skills(memory_dir: Path, force: bool = False) -> int:
    seed_dir = TEMPLATES_DIR / "skills" / "seed"
    skills_dir = memory_dir / "skills"
    skills_dir.mkdir(parents=True, exist_ok=True)
    copied_count = 0
    for skill_file in seed_dir.glob("*.md"):
        dest = skills_dir / skill_file.name
        if force or not dest.exists():
            shutil.copy(skill_file, dest)
            copied_count += 1
    total_skills = len(list(skills_dir.glob("*.md")))
    return total_skills


def has_existing_code(project_dir: Path) -> bool:
    extensions = {".py", ".js", ".ts", ".go", ".rb", ".java", ".cs"}
    return any(f.suffix in extensions for f in project_dir.rglob("*") if f.is_file())


def _print_init_success(name: str, seed_count: int) -> None:
    console.print(f"[green]Project '{name}' initialized[/green]")
    console.print(
        f"[green]{seed_count} seed skills loaded into ~/.prism/memory/skills/[/green]"
    )


def init_project(project_dir: Path) -> None:
    ensure_global_config()
    project_dir.mkdir(parents=True, exist_ok=True)
    prism_dir = create_prism_dir(project_dir)
    write_prism_files(prism_dir, project_dir.name)
    setup_prism_spec(project_dir)
    memory_dir = init_global_memory()
    count = seed_skills(memory_dir)
    _print_init_success(project_dir.name, count)


def attach_project(project_dir: Path) -> None:
    ensure_global_config()
    if has_prism_spec(project_dir):
        console.print("[green]PRISM Spec already initialized[/green]")
    else:
        setup_prism_spec(project_dir)
    prism_dir = create_prism_dir(project_dir)
    write_prism_files(prism_dir, project_dir.name)
    memory_dir = init_global_memory()
    seed_skills(memory_dir)
    console.print(f"[green]PRISM attached to '{project_dir.name}'[/green]")
