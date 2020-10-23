#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""create a cell and export to various code-specific format

Use `-s` for creating from predefined sample, stored in `db/cell`.
Use `--show` for curating available samples.
"""
import pathlib
from argparse import ArgumentParser, RawDescriptionHelpFormatter
from mushroom.core.cell import Cell
from mushroom.core.logger import create_logger

cell_db = pathlib.Path(__file__).parent.parent / "db" / "cell"
_logger = create_logger("buildc", f_handler=False)
del create_logger

def curate_samples():
    """curate avail samples"""
    for i, s in enumerate(get_avail_samples()):
        print("{:>3d}: {:s}".format(i, s))

def get_avail_samples():
    """get available choices of cell sample"""
    search = ["*.cif",
              "**/*.cif",
              "*.json",
              "**/*.json",
              ]
    d = []
    for s in search:
        d.extend(str(x.relative_to(cell_db)) for x in cell_db.glob(s))
    return d

def get_cell_sample(sample):
    """get the Cell instance from predefined sample data

    Args:
        sample (str or int)
    """
    try:
        sample = get_avail_samples()[int(sample)]
    except ValueError:
        pass
    p = cell_db / sample
    return Cell.read(p)

def _parser():
    """parser"""
    parser = ArgumentParser(description=__doc__, formatter_class=RawDescriptionHelpFormatter)
    parser.add_argument('-o', dest='output_format', type=str, choices=Cell.avail_exporters,
                        default=Cell.avail_exporters[0], help="output format")
    igrp = parser.add_mutually_exclusive_group()
    igrp.add_argument('-I', dest='input_file', type=str, default=None, help="input file")
    igrp.add_argument('-s', dest='sample', type=str, default=None, 
                      help="extract predefined sample. int or str. see --show")
    igrp.add_argument('--show', action="store_true",
                      help="show predefined sample")
    parser.add_argument('-a', dest='add_sample', action="store_true",
                        help="add converted input to sample data (JSON format)")
    parser.add_argument('-i', dest='input_format', type=str,
                        help="format of input file, automatic detection (TODO)")
    parser.add_argument('-O', dest='output_file', type=str, default=None,
                        help="output file")
    return parser.parse_args()

    
def build_cell():
    """main stream"""
    args = _parser()
    if args.input_file:
        if args.add_sample:
            pass
        raise NotImplementedError
    if args.sample:
        c = get_cell_sample(args.sample)
        c.export(args.output_format, filename=args.output_file)
        return
    if args.show:
        curate_samples()
        return

    raise ValueError("specify -I / -s / --show")


if __name__ == "__main__":
    build_cell()

