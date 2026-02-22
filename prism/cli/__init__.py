import click

from prism import __version__
from .approve import approve_pr
from .attach import attach
from .augment import augment
from .board import board
from .config_cmd import config
from .generate_context import generate_context
from .health import health
from .index import index
from .inject import inject
from .init import init
from .memory import memory
from .optimize import optimize
from .reject import reject_pr
from .resume import resume
from .review import review
from .schedule import schedule
from .seed import seed
from .shell import shell
from .skill import skill
from .start import start
from .submit import submit_for_qa
from .sync import sync
from .task import task


@click.group()
@click.version_option(version=__version__, prog_name="prism")
def main() -> None:
    """PRISM — Project Reasoning & Intelligent Skill Memory.

    Agent-agnostic orchestration with cross-project skill memory.
    """


main.add_command(init)
main.add_command(attach)
main.add_command(config)
main.add_command(seed)
main.add_command(skill)
main.add_command(index)
main.add_command(inject)
main.add_command(memory)
main.add_command(board)
main.add_command(augment)
main.add_command(sync)
main.add_command(task)
main.add_command(start)
main.add_command(resume)
main.add_command(generate_context)
main.add_command(health)
main.add_command(optimize)
main.add_command(schedule)

# Pipeline & QA commands
main.add_command(submit_for_qa)
main.add_command(review)
main.add_command(approve_pr)
main.add_command(reject_pr)
main.add_command(shell)
