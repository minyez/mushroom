# -*- coding: utf-8 -*-
"""Unified command line entry of mushroom

The subcommands under each code group dispatch to the scripts in the
``scripts`` directory. Arguments after the subcommand are passed to the
script untouched, so ``mushroom aims band -h`` shows the help of ``m_aims_band``.
"""
import ast
import runpy
import sys
from pathlib import Path

import click

from mushroom import __version__
from mushroom.detect import detect_codes

SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"

# group name -> (group help, {subcommand: script name})
# group name None means the subcommand is attached to the top level
SCRIPT_COMMANDS = {
    "aims": ("FHI-aims utilities", {
        "append-basis": "m_aims_append_basis",
        "band": "m_aims_band",
        "check-finish": "m_aims_check_dir_finish",
        "check-ob-ortho": "m_aims_check_ob_ortho",
        "control": "m_aims_control",
        "dim": "m_aims_dim_stdout",
        "gap": "m_aims_gap",
        "get-input": "m_aims_get_input_from_stdout",
        "prepare-control": "m_aims_prepare_control",
        "qp-corr": "m_aims_qp_corr_stdout",
        "qp-dos": "m_aims_qp_dos_stdout",
        "qp-gap": "m_aims_qp_gap_stdout",
    }),
    "vasp": ("VASP utilities", {
        "band": "m_vasp_band",
        "chg": "m_vasp_chg",
        "dos": "m_vasp_dos",
        "gap": "m_vasp_gap",
        "pwav": "m_vasp_pwav",
    }),
    "w2k": ("WIEN2k utilities", {
        "band": "m_w2k_band",
        "dos": "m_w2k_dos",
        "gap": "m_w2k_gap",
    }),
    "gap": ("GAP utilities", {
        "analyze-eqpev": "m_gap_analyze_eqpev",
        "degw": "m_gap_degw",
        "eps": "m_gap_eps",
        "vmat": "m_gap_vmat",
    }),
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


@click.group(context_settings={"help_option_names": ["-h", "--help"]})
@click.version_option(__version__, "-V", "--version", prog_name="mushroom")
def main():
    """mushroom, a Multi-fUnctional, Simple and Helpful Research tOOlkit for Material science"""


@main.command()
@click.argument("dirpaths", nargs=-1, type=click.Path(exists=True, file_okay=False))
@click.option("-q", "--quiet", is_flag=True,
              help="print only the short name of the most probable code")
def detect(dirpaths, quiet):
    """detect which code the calculation in a directory belongs to

    DIRPATHS defaults to the current directory. Exit with 1 if no code is
    detected in any directory.
    """
    if not dirpaths:
        dirpaths = (".",)
    found_any = False
    for dirpath in dirpaths:
        results = detect_codes(dirpath)
        found_any = found_any or bool(results)
        if quiet:
            if results:
                click.echo(results[0].code if len(dirpaths) == 1 else f"{dirpath}: {results[0].code}")
            continue
        click.echo(f"{click.format_filename(Path(dirpath).resolve())}:")
        if not results:
            click.echo("  no known calculation detected")
        for r in results:
            click.echo(f"  {r.code:8s} {r.name} (score {r.score})")
            for e in r.evidences:
                click.echo(f"           {e}")
    if not found_any:
        sys.exit(1)


for _group, (_help, _commands) in SCRIPT_COMMANDS.items():
    if _group is None:
        _parent = main
    else:
        _parent = click.Group(_group, help=_help,
                              context_settings={"help_option_names": ["-h", "--help"]})
        main.add_command(_parent)
    for _name, _script in _commands.items():
        _parent.add_command(ScriptCommand(_name, _script))


if __name__ == "__main__":
    main()
