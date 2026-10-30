# -*- coding: utf-8 -*-
"""Crystal cell commands

Modules heavier than click are imported inside the commands to keep the entry fast.
"""
import click

from mushroom.cli._utils import Group, check_exclusive, multi_option

# same as mushroom.io.CellIO.avail_readers and avail_writers,
# which are not imported here to keep the entry fast
_READERS = ("vasp", "json", "cif", "aims", "abacus", "w2k")
_WRITERS = ("vasp", "abi", "json", "qe", "qe_alat", "aims", "abacus", "w2k")


@click.group(cls=Group)
def cell():
    """crystal cell utilities"""


def _write_transformation_matrix(supercell):
    """write the transformation matrix of supercell"""
    with open("transformation_matrix.dat", 'w') as h:
        if len(supercell) == 1:
            print(supercell[0], 0, 0, file=h)
            print(0, supercell[0], 0, file=h)
            print(0, 0, supercell[0], file=h)
        elif len(supercell) == 3:
            print(supercell[0], 0, 0, file=h)
            print(0, supercell[1], 0, file=h)
            print(0, 0, supercell[2], file=h)
        elif len(supercell) == 9:
            print(supercell[0], supercell[1], supercell[2], file=h)
            print(supercell[3], supercell[4], supercell[5], file=h)
            print(supercell[6], supercell[7], supercell[8], file=h)


@cell.command()
@click.option("-I", "input_file", default=None, help="input file")
@click.option("-f", "search", default=None,
              help="search and print out cells with file names matching the regex")
@click.option("-c", "sample", default=None,
              help="extract predefined sample cell. int or str. see -l")
@click.option("-l", "show", is_flag=True, help="list predefined sample cells")
@multi_option("--sc", "supercell", type=int, metavar="N...", help="create super cell")
@click.option("--coord", "coord_system", default="D", type=click.Choice(["d", "c", "D", "C"]),
              help="coordinate system of output, direct or Cartesian")
@click.option("--prim", "primitize", is_flag=True, help="primitize the cell (spglib required)")
@click.option("--std", "standardize", is_flag=True, help="standardize the cell (spglib required)")
@click.option("-i", "input_format", type=click.Choice(_READERS), default=None,
              help="format of input file, default use automatic detection")
@click.option("--db", "db_cell_path", default=None, help="(absolute) path of the cell database")
@click.option("-O", "output_path", default=None, help="output file")
@click.option("-o", "output_format", type=click.Choice(_WRITERS), default=None, help="output format")
@click.pass_context
def convert(ctx, input_file, search, sample, show, supercell, coord_system, primitize, standardize,
            input_format, db_cell_path, output_path, output_format):
    """create/read a cell and export to various code-specific format

    \b
    Use `-I` for converting file of one cell format to another
    Use `-c` for creating from predefined sample, stored in `db/cell`.
    Use `-l` for curating available cell samples.
    """
    from os.path import isfile

    from mushroom.db import DBCell
    from mushroom.io import CellIO

    check_exclusive(ctx, "input_file", "search", "sample", "show")
    if input_file is not None:
        if not isfile(input_file):
            raise FileNotFoundError(input_file)
    else:
        # cell database operations
        cdb = DBCell(db_cell_path)
        if sample is not None:
            input_file = cdb.get_cell_path(sample)
        elif show or search:
            if cdb.N == 0:
                print("No cell entries are found at", cdb._db_path)
            for i, s in cdb.filter(search):
                print("{:>3d} : {:s}".format(i, s))
            return
        else:
            raise click.UsageError("specify one of -I, -f, -c and -l", ctx=ctx)

    supercell = list(supercell) or None
    cio = CellIO(input_file, format=input_format)
    # super cell mapping
    mapping = cio.manipulate(primitize=primitize, standardize=standardize, supercell=supercell)
    cio.write(output_path=output_path, format=output_format, coord_system=coord_system.upper())

    # Dump super-cell information
    # TODO: hard coded mapping export
    if mapping is not None:
        with open("unfolding_map.dat", 'w') as h:
            for i in mapping:
                print(i + 1, file=h)
    # Write transformation matrix, support diagonal only
    if supercell is not None:
        _write_transformation_matrix(supercell)


@cell.command()
@click.argument("input_cell")
@click.option("-i", "input_format", default=None, help="Format of input file")
@click.option("-r", "sym_per_row", is_flag=True, help="print each symmetry operation in one row")
@click.option("-s", "sort_operations", is_flag=True,
              help="sort symmetry operations by rotation matrix")
def info(input_cell, input_format, sym_per_row, sort_operations):
    """Show the symmetry of input structure"""
    from mushroom.core.cell import Cell
    from mushroom.core.crystutils import (display_symmetry_info, get_density,
                                          get_latt_consts_from_latt_vecs)
    try:
        import spglib
    except ImportError:
        spglib = None

    c = Cell.read(input_cell, format=input_format)
    density_n, density_m = get_density(c.latt, c.atms, latt_unit=c.unit)
    print("Number density (per ang^3):", density_n)
    print("Mass density (kg per m^3):", density_m)
    lattcon = get_latt_consts_from_latt_vecs(c.latt)
    print("Lattice constants (abc, alpha/beta/gamma):",
          lattcon[0], lattcon[1], lattcon[2],
          lattcon[3], lattcon[4], lattcon[5])
    if spglib is None:
        print("Spglib not avaiable, skip symmetry analysis")
    else:
        display_symmetry_info(*(c.get_spglib_input()), print_sym_per_row=sym_per_row,
                              sort_operations=sort_operations)
