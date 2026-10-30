# -*- coding: utf-8 -*-
"""LibRPA commands

Modules heavier than click are imported inside the commands to keep the entry fast.
"""
import click

from mushroom.cli._utils import Group, opt_trans


@click.group(cls=Group)
def librpa():
    """LibRPA utilities"""


@librpa.command()
@click.argument("stdout")
@click.option("--use-occ-only", is_flag=True,
              help="only use occupation number to detect band edges, instead of using both energy and occ")
@click.option("--kind", default="qp", type=click.Choice(["qp", "ks", "exx"]),
              help="Type of band to check")
@click.option("-v", "--value", "value_only", is_flag=True,
              help="show values only when displaying band")
@opt_trans
def gap(stdout, use_occ_only, kind, value_only, trans):
    """extract the band gap from LibRPA standard output"""
    from mushroom.core.bs import display_band_analysis, display_transition_energies
    from mushroom.librpa import read_quasi_particle_energies_stdout

    bs, kpts = read_quasi_particle_energies_stdout(stdout, kind=kind, unit="ev",
                                                   use_occ_only=use_occ_only)
    display_band_analysis(bs, kpts, value_only=value_only)
    if trans:
        display_transition_energies(trans, bs, kpts, value_only=value_only)
