# -*- coding: utf-8 -*-
"""Unified command line entry of mushroom

Each group of commands lives in its own module.
"""
import sys

import click

from mushroom import __version__
from mushroom.cli.aims import aims
from mushroom.cli.cell import cell
from mushroom.cli.detect import detect
from mushroom.cli.gap import gap
from mushroom.cli.job import job
from mushroom.cli.kpt import kpt
from mushroom.cli.librpa import librpa
from mushroom.cli.tools import doctemp, fiteos, quickgrace, workflow
from mushroom.cli.vasp import vasp
from mushroom.cli.w2k import w2k


@click.group(context_settings={"help_option_names": ["-h", "--help"]})
@click.version_option(__version__, "-V", "--version", prog_name="mushroom")
def main():
    """mushroom, a Multi-fUnctional, Simple and Helpful Research tOOlkit for Material science"""


for _command in (aims, cell, detect, doctemp, fiteos, gap, job, kpt, librpa, quickgrace, vasp, w2k,
                 workflow):
    main.add_command(_command)


def run_deprecated(*subcommand):
    """entry of a deprecated script, which forwards to a mushroom subcommand"""
    new = " ".join(("mushroom",) + subcommand)
    print(f"Warning: this script is deprecated, use \"{new}\" instead", file=sys.stderr)
    main(args=[*subcommand, *sys.argv[1:]], prog_name="mushroom")
