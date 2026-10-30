# -*- coding: utf-8 -*-
"""Unified command line entry of mushroom

Each code group of native click commands lives in its own module. The groups
not migrated yet dispatch to the scripts, see :mod:`mushroom.cli._dispatch`.
"""
import sys

import click

from mushroom import __version__
from mushroom.cli._dispatch import SCRIPT_COMMANDS, SCRIPTS_DIR, ScriptCommand
from mushroom.cli.aims import aims
from mushroom.cli.cell import cell
from mushroom.cli.detect import detect
from mushroom.cli.gap import gap
from mushroom.cli.kpt import kpt
from mushroom.cli.vasp import vasp
from mushroom.cli.w2k import w2k

_CONTEXT_SETTINGS = {"help_option_names": ["-h", "--help"]}


@click.group(context_settings=_CONTEXT_SETTINGS)
@click.version_option(__version__, "-V", "--version", prog_name="mushroom")
def main():
    """mushroom, a Multi-fUnctional, Simple and Helpful Research tOOlkit for Material science"""


main.add_command(aims)
main.add_command(cell)
main.add_command(detect)
main.add_command(gap)
main.add_command(kpt)
main.add_command(vasp)
main.add_command(w2k)

for _group, (_help, _commands) in SCRIPT_COMMANDS.items():
    if _group is None:
        _parent = main
    else:
        _parent = click.Group(_group, help=_help, context_settings=_CONTEXT_SETTINGS)
        main.add_command(_parent)
    for _name, _script in _commands.items():
        _parent.add_command(ScriptCommand(_name, _script))


def run_deprecated(*subcommand):
    """entry of a deprecated script, which forwards to a mushroom subcommand"""
    new = " ".join(("mushroom",) + subcommand)
    print(f"Warning: this script is deprecated, use \"{new}\" instead", file=sys.stderr)
    main(args=[*subcommand, *sys.argv[1:]], prog_name="mushroom")
