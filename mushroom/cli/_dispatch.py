# -*- coding: utf-8 -*-
"""Dispatch subcommands to the scripts not migrated to native click yet

Arguments after the subcommand are passed to the script untouched, so
``mushroom vasp band -h`` shows the help of ``m_vasp_band``.
"""
import ast
import runpy
import sys
from pathlib import Path

import click

SCRIPTS_DIR = Path(__file__).resolve().parents[2] / "scripts"

# group name -> (group help, {subcommand: script name})
# group name None means the subcommand is attached to the top level
SCRIPT_COMMANDS = {
    "librpa": ("LibRPA utilities", {
        "gap": "m_librpa_gap",
    }),
    "cell": ("crystal cell utilities", {
        "convert": "m_cell",
        "info": "m_cell_info",
    }),
    "kpt": ("k-point utilities", {
        "kmesh": "m_kpt_get_kmesh",
    }),
    "job": ("HPC job utilities", {
        "add-header": "m_job_add_header",
        "submit": "m_job_submit",
    }),
    None: (None, {
        "doctemp": "m_doctemp",
        "fiteos": "m_fiteos",
        "quickgrace": "m_quickgrace",
        "workflow": "m_workflow",
    }),
}


def _script_summary(script: Path) -> str:
    """first line of the module docstring of a script"""
    try:
        doc = ast.get_docstring(ast.parse(script.read_text()))
    except (OSError, SyntaxError):
        doc = None
    if not doc:
        return f"run {script.name}"
    return doc.strip().splitlines()[0]


def run_script(script: Path, args):
    """run a script as __main__ with arguments args"""
    argv_orig = sys.argv
    # runpy sets sys.argv[0] to the script path
    sys.argv = [str(script), *args]
    try:
        runpy.run_path(str(script), run_name="__main__")
    finally:
        sys.argv = argv_orig


class ScriptCommand(click.Command):
    """command that passes all its arguments to a script"""

    def __init__(self, name: str, script: str):
        super().__init__(name, add_help_option=False,
                         context_settings={"ignore_unknown_options": True,
                                           "allow_extra_args": True})
        self.params = [click.Argument(["args"], nargs=-1, type=click.UNPROCESSED)]
        self.script = SCRIPTS_DIR / script

    def get_short_help_str(self, limit: int = 45) -> str:
        # read the docstring only when the help is printed
        return click.utils.make_default_short_help(_script_summary(self.script), limit)

    def invoke(self, ctx: click.Context):
        run_script(self.script, ctx.params["args"])
