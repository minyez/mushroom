# -*- coding: utf-8 -*-
"""functionality for IO"""
import os
from typing import Union, List

from mushroom.core.pkg import detect
from mushroom.core.logger import loggers
# For CellIO
from mushroom.core.cell import Cell
from mushroom.w2k import Struct

_logger = loggers["io"]

__all__ = [
    "CellIO",
]


class AtomsIO:
    """"""


class CellIO:
    """Read, manipulate and """
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
                   **kwargs) -> Union[None, List[int]]:
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
            retval: List[int]
            self._cell, retval = self._cell.get_supercell(*supercell, **kwargs)
        return retval

    def write(self, output_path: Union[str, os.PathLike] = None, format: str = None) -> None:
        """write the cell to ``output_path`` in the format of program ``format``
        Args:
            output_path (path-like)
            format (str): identifier for program
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
                self._struct.get_cell().write(format, filename=output_path)
            return

        # writer for a non-wien2k read-in cell
        if format == "w2k":
            Struct.from_cell(self._cell).write(filename=output_path)
        else:
            self._cell.write(format, filename=output_path)


def read_elsi_to_csc(fn, verbose=False):
    """Read ELSI CSC file format.

    Adapted from the same function in FHI-aims utitlities

    Args:
        fn (str) : path to the ELSI CSC file
        verbose (bool) : verbositiy control

    Retunrs:
        scipy sparse matrix
    """
    import struct
    import scipy.sparse as sp
    import numpy as np

    mat = open(fn, "rb")
    data = mat.read()
    mat.close()
    i8 = "l"
    i4 = "i"

    # Get header
    start = 0
    end = 128
    header = struct.unpack(i8 * 16, data[start:end])
    if verbose:
        print(header)

    # Number of basis functions (matrix size)
    n_basis = header[3]

    # Total number of non-zero elements
    nnz = header[5]

    # Get column pointer
    start = end
    end = start + n_basis * 8
    col_ptr = struct.unpack(i8 * n_basis, data[start:end])
    # print(col_ptr)
    col_ptr += (nnz + 1, )
    col_ptr = np.array(col_ptr)

    # Get row index
    start = end
    end = start + nnz * 4
    row_idx = struct.unpack(i4 * nnz, data[start:end])
    row_idx = np.array(row_idx)

    # Get non-zero value
    start = end

    if header[2] == 0:
        if verbose:
            print("Reading real matrix")
        # Real case
        end = start + nnz * 8
        nnz_val = struct.unpack("d" * nnz, data[start:end])
    else:
        if verbose:
            print("Reading complex matrix")
        # Complex case
        end = start + nnz * 16
        nnz_val = struct.unpack("d" * nnz * 2, data[start:end])
        nnz_val_real = np.array(nnz_val[0::2])
        nnz_val_imag = np.array(nnz_val[1::2])
        nnz_val = nnz_val_real + 1j * nnz_val_imag

    nnz_val = np.array(nnz_val)

    # Change convention to starting index from 0
    for i_val in range(nnz):
        row_idx[i_val] -= 1

    for i_col in range(n_basis + 1):
        col_ptr[i_col] -= 1

    return sp.csc_matrix((nnz_val, row_idx, col_ptr), shape=(n_basis, n_basis))
