# -*- coding: utf-8 -*-
"""functionality for IO"""
import os
from typing import Union

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

    def manipulate(self, primitize=False, standardize=False, no_idealize=False, supercell=None) -> None:
        """manipulate the read cell"""
        if self._format_read == "w2k":
            if primitize or standardize:
                raise NotImplementedError("primitive w2k format is not supported")
        if standardize:
            self._cell = self._cell.standardize(to_primitive=primitize, no_idealize=no_idealize)
        else:
            if primitize:
                self._cell = self._cell.primitize()
        if supercell:
            self._cell = self._cell.get_supercell(*supercell)

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

