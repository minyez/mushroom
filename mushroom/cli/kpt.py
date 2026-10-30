# -*- coding: utf-8 -*-
"""k-point commands

Modules heavier than click are imported inside the commands to keep the entry fast.
"""
import click

from mushroom.cli._utils import Group


@click.group(cls=Group)
def kpt():
    """k-point utilities"""


@kpt.command()
@click.argument("kgrids", nargs=3, type=int)
@click.option("--ir", is_flag=True, help="flag to get irreducile points")
@click.option("--gamma-center", is_flag=True, help="flag to generate Gamma-centered mesh")
@click.option("-I", "inputcell", default=None, help="cell input file")
@click.option("-i", "input_format", default=None, help="format of cell input file")
@click.pass_context
def kmesh(ctx, kgrids, ir, gamma_center, inputcell, input_format):
    """compute the k-point mesh of a k-grids"""
    from mushroom.core.cell import Cell
    from mushroom.core.kpoints import MPGrid

    spgcell = None
    if ir:
        if inputcell is None:
            raise click.UsageError("Cell input -I is required to get irreducible kmesh", ctx=ctx)
        spgcell = Cell.read(inputcell).get_spglib_input()

    mpgrids = MPGrid(kgrids[0], kgrids[1], kgrids[2], spgcell)
    if ir:
        kpts, mapping = mpgrids.get_ir_grids()
    else:
        kpts = mpgrids.kpts
        mapping = list(range(len(kpts)))
    for i, (k, mapirk) in enumerate(zip(kpts, mapping)):
        if i == mapirk:
            print("%3d %8.5f %8.5f %8.5f" % (i + 1, k[0], k[1], k[2]))
        else:
            print("%3d %8.5f %8.5f %8.5f -> %3d %8.5f %8.5f %8.5f" %
                  (i + 1, k[0], k[1], k[2], mapirk + 1,
                   kpts[mapirk][0], kpts[mapirk][1], kpts[mapirk][2]))
