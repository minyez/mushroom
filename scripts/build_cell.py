#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""create a cell and export to various code-specific format

Use `-s` for creating from predefined sample, stored in `db/cell`.
Use `--show` for curating available samples.
"""
from argparse import ArgumentParser, RawDescriptionHelpFormatter
from mushroom.core.db import DBCell
from mushroom.core.cell import Cell, CellError
from mushroom.w2k import Struct

def _parser():
    """parser"""
    parser = ArgumentParser(description=__doc__, formatter_class=RawDescriptionHelpFormatter)
    parser.add_argument('-o', dest='output_format', type=str,
                        choices=["vasp", "abi", "json", "w2k"],
                        default=Cell.avail_exporters[0], help="output format")
    igrp = parser.add_mutually_exclusive_group()
    igrp.add_argument('-I', dest='input_file', type=str, default=None, help="input file")
    igrp.add_argument('--filter', dest="search", type=str, default=None,
                      help="search and print out cells with file names matching the regex")
    igrp.add_argument('-s', dest='sample', default=None, 
                      help="extract predefined sample. int or str. see --show")
    igrp.add_argument('-p', dest='show', action="store_true",
                      help="show predefined sample")
    parser.add_argument('-a', dest='add_sample', type=str, default=None,
                        help="add converted input to sample data (JSON format)")
    parser.add_argument('-i', dest='input_format', type=str, default=None,
                        help="format of input file, automatic detection (TODO)")
    parser.add_argument('-O', dest='output_file', type=str, default=None,
                        help="output file")
    return parser.parse_args()

    
def build_cell():
    """main stream"""
    args = _parser()
    cdb = DBCell()
    if args.input_file and args.add_sample:
        try:
            c = Cell.read(args.input_file, form=args.input_format)
        except CellError:
            if args.input_file.endswith(".struct") or args.input_format == "w2k":
                c = Struct.read(args.input_file).get_cell()
        if args.output_format in Cell.avail_exporters:
            s = c.export(args.output_format)
        else:
            raise ValueError("adding format {} is not supported".format(args.output_format))
        cdb.add_entry(args.add_sample, s)
        return
    if args.sample is not None:
        c = Cell.read(cdb.get_entry_path(args.sample))
        if args.output_format in Cell.avail_exporters:
            c.write(args.output_format, filename=args.output_file)
        elif args.output_format == "w2k":
            Struct.from_cell(c).write(filename=args.output_file)
        else:
            raise ValueError("output format {} is not supported".format(args.output_format))
        return
    if args.show or args.search:
        for i, s in cdb.filter(args.search):
            print("{:>3d} : {:s}".format(i, s))
        return

    raise ValueError("specify -I / --filter / -s / -p")


if __name__ == "__main__":
    build_cell()

