from __future__ import annotations

import os
import shutil
import subprocess
import sys
from datetime import date
from pathlib import Path

from rich.console import Console

from prism.config import GLOBAL_CONFIG_DIR, GLOBAL_CONFIG_PATH

console = Console()
TEMPLATES_DIR = Path(__file__).parent / "templates"


def check_speckit() -> bool:
    return shutil.which("specify") is not None


def check_docker() -> bool:
    return shutil.which("docker") is not None


def is_interactive_terminal() -> bool:
    """Check if we're running in an interactive terminal (TTY available)."""
    return sys.stdin.isatty() and sys.stdout.isatty()


def _speckit_env() -> dict[str, str]:
    env = os.environ.copy()
    env.pop("GITHUB_TOKEN", None)
    env.pop("GH_TOKEN", None)
    return env


def _run_speckit(cmd: list[str], cwd: str | None = None) -> int:
    try:
        result = subprocess.run(
            cmd,
            env=_speckit_env(),
            cwd=cwd,
            timeout=120,
            stderr=subprocess.PIPE,
            text=True,
        )
        if result.returncode != 0 and result.stderr:
            console.print(f"[dim]{result.stderr.strip()}[/dim]")
        return result.returncode
    except subprocess.TimeoutExpired:
        console.print("[yellow]⚠️  specify timed out after 120s[/yellow]")
        return 1


def run_speckit_init(project_dir: Path) -> int:
    return _run_speckit(
        ["specify", "init", str(project_dir), "--ai", "claude", "--script", "sh"],
    )


def run_speckit_here(project_dir: Path) -> int:
    return _run_speckit(
        ["specify", "init", ".", "--here", "--ai", "claude", "--script", "sh"],
        cwd=str(project_dir),
    )


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
    # Return total count of skills in memory, not just newly copied
    total_skills = len(list(skills_dir.glob("*.md")))
    return total_skills


def has_speckit(project_dir: Path) -> bool:
    return (project_dir / ".specify").exists()


def has_existing_code(project_dir: Path) -> bool:
    extensions = {".py", ".js", ".ts", ".go", ".rb", ".java", ".cs"}
    return any(f.suffix in extensions for f in project_dir.rglob("*") if f.is_file())


def _try_speckit_init(project_dir: Path) -> None:
    if not check_speckit():
        console.print("[yellow]⚠️  specify (Spec-Kit) not found — skipping[/yellow]")
        return
    if project_dir.exists():
        console.print(
            "[yellow]⚠️  Project directory already exists — skipping Spec-Kit init[/yellow]"
        )
        return
    if not is_interactive_terminal():
        console.print(
            "[yellow]⚠️  Non-interactive terminal detected — skipping Spec-Kit (requires TTY)[/yellow]"
        )
        return
    rc = run_speckit_init(project_dir)
    if rc == 0:
        console.print("[green]✅ Spec-Kit initialized[/green]")
    else:
        console.print(
            "[yellow]⚠️  specify init failed — continuing without Spec-Kit[/yellow]"
        )


def _try_speckit_here(project_dir: Path) -> None:
    if not check_speckit():
        console.print("[yellow]⚠️  specify not found — skipping Spec-Kit setup[/yellow]")
        return
    if not is_interactive_terminal():
        console.print(
            "[yellow]⚠️  Non-interactive terminal — skipping Spec-Kit[/yellow]"
        )
        return
    rc = run_speckit_here(project_dir)
    if rc == 0:
        console.print("[green]✅ Spec-Kit initialized[/green]")
    else:
        console.print("[yellow]⚠️  specify init failed — continuing[/yellow]")


def _print_init_success(name: str, seed_count: int) -> None:
    console.print(f"[green]✅ Project '{name}' initialized[/green]")
    console.print(
        f"[green]✅ {seed_count} seed skills loaded into ~/.prism/memory/skills/[/green]"
    )


def init_project(project_dir: Path, skip_speckit: bool = False) -> None:
    ensure_global_config()
    if not skip_speckit:
        if project_dir.exists():
            console.print(
                "[yellow]⚠️  Project directory already exists — skipping Spec-Kit init[/yellow]"
            )
        else:
            _try_speckit_init(project_dir)
    project_dir.mkdir(parents=True, exist_ok=True)
    prism_dir = create_prism_dir(project_dir)
    write_prism_files(prism_dir, project_dir.name)
    memory_dir = init_global_memory()
    count = seed_skills(memory_dir)
    _print_init_success(project_dir.name, count)


def attach_project(project_dir: Path) -> None:
    ensure_global_config()
    if not has_speckit(project_dir):
        _try_speckit_here(project_dir)
    else:
        console.print("[green]✅ Spec-Kit already initialized[/green]")
    prism_dir = create_prism_dir(project_dir)
    write_prism_files(prism_dir, project_dir.name)
    memory_dir = init_global_memory()
    seed_skills(memory_dir)
    console.print(f"[green]✅ PRISM attached to '{project_dir.name}'[/green]")
