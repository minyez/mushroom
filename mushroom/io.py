# -*- coding: utf-8 -*-
"""functionality for IO"""
import os
from typing import Union, Optional

import numpy as np

from mushroom.core.pkg import detect
from mushroom.core.logger import loggers
# For CellIO
from mushroom.core.cell import Cell
from mushroom.w2k import Struct

_logger = loggers["io"]

__all__ = [
    "CellIO",
]


class CellIO:
    """Read, manipulate and"""

    avail_writers = list(Cell.avail_exporters) + ["w2k", ]
    avail_readers = list(Cell.avail_readers) + ["w2k", ]

    default_writer = "vasp"
    assert default_writer in avail_writers

    def __init__(self, path_cell: str, format=None):
        if format is None:
            format = detect(path_cell, fail_with_ext=True)
        if format not in self.avail_readers:
            raise ValueError("unsupported format for reading cell: {}".format(format))

        if format == "w2k":
            c = None
            s = Struct.read(path_cell)
        else:
            c = Cell.read(path_cell, format=format)
            s = None
        _logger.info("Reading %r with format %s", path_cell, format)

        self._format_read = format
        self._cell: Cell = c
        self._struct: Struct = s

    def manipulate(self, primitize=False, standardize=False, no_idealize=False, supercell=None,
                   **kwargs) -> Union[None, list[int]]:
        """manipulate the read cell"""
        if self._format_read == "w2k":
            if primitize or standardize:
                raise NotImplementedError("primitive w2k format is not supported")
        retval = None
        if standardize:
            self._cell = self._cell.standardize(to_primitive=primitize, no_idealize=no_idealize)
        else:
            if primitize:
                self._cell = self._cell.primitize()
        if supercell:
            retval: list[int]
            self._cell, retval = self._cell.get_supercell(*supercell, **kwargs)
        return retval

    def write(self, output_path: Optional[Union[str, os.PathLike]] = None, format: Optional[str] = None, coord_system: str = "D") -> None:
        """write the cell to ``output_path`` in the format of program ``format``

        Args:
            output_path (path-like): output structure path, or None to print to stdout
            format (str): identifier for program
            coord_system (str): direct or cartesian, except for wien2k
        """
        if format is None:
            if output_path is None:
                format = self._format_read
                _logger.debug("output not specfied, using same format as read: %s", format)
            else:
                format = detect(output_path)
            if not format:
                format = self.default_writer
                _logger.debug("fail to detect a format for writing cell, use default writer: %s",
                              format)

        _logger.info("Writing to %r with format %s", output_path, format)

        if self._format_read == "w2k":
            if format == "w2k":
                self._struct.write(filename=output_path)
            else:
                c = self._struct.get_cell()
                with c.temporary_representation(coord_sys=coord_system):
                    c.write(format, filename=output_path)
            return

        # writer for a non-wien2k read-in cell
        if format == "w2k":
            Struct.from_cell(self._cell).write(filename=output_path)
        else:
            with self._cell.temporary_representation(coord_sys=coord_system):
                self._cell.write(format, filename=output_path)


def read_elsi_to_csc(fn, verbose=False):
    """Read ELSI CSC file format.

    Adapted from the same function in FHI-aims utitlities

    Args:
        fn (str): path to the ELSI CSC file
        verbose (bool): verbositiy control

    Returns:
        scipy sparse matrix
    """
    # Keep scipy optional at module import time.
    import scipy.sparse as sp

    with open(fn, "rb") as handle:
        data = handle.read()
    header = np.frombuffer(data, dtype="<i8", count=16)
    n_basis, nnz = int(header[3]), int(header[5])
    if verbose:
        _logger.info("ELSI header: %s", header)
        _logger.info("Reading %s matrix", "complex" if header[2] else "real")
    offset = 128
    col_ptr = np.append(np.frombuffer(data, dtype="<i8", count=n_basis, offset=offset), nnz + 1) - 1
    offset += n_basis * 8
    row_idx = np.frombuffer(data, dtype="<i4", count=nnz, offset=offset) - 1
    offset += nnz * 4
    dtype = "<c16" if header[2] else "<f8"
    # CSC values are writable, matching the former array constructor.
    values = np.frombuffer(data, dtype=dtype, count=nnz, offset=offset).copy()
    return sp.csc_matrix((values, row_idx, col_ptr), shape=(n_basis, n_basis))
