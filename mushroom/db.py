# -*- coding: utf-8 -*-
"""database related"""
import pathlib
from re import search
from os import makedirs
from shutil import copy
from collections.abc import Iterable
from typing import Union

from mushroom.core.logger import create_logger
from mushroom.core.cell import Cell
from mushroom.w2k import Struct
from mushroom.core.pkg import detect

__all__ = [
        "DBCell",
        "DBWorkflow",
        "DBKPath",
        ]

_logger = create_logger("db")
del create_logger

# database directory of mushroom
mushroom_db_home = pathlib.Path(__file__).parent.parent / "db"

if not mushroom_db_home.is_dir():
    raise FileNotFoundError("database directory is not found", mushroom_db_home.name)

class DBEntryNotFoundError(FileNotFoundError):
    """exception for failing to find database entry"""

class _DBBase:
    """base object of database searching

    Args:
        name (str) : relative path for databse in mushroom. otherwise
        glob_regex (Iterable)
    """
    def __init__(self, name: str, glob_regex: Iterable):
        name = pathlib.Path(name)
        if name.is_absolute():
            self._db_path = name
        else:
            self._db_path = mushroom_db_home / name
        self._glob = glob_regex
        self._available_entries = None
        if not isinstance(glob_regex, Iterable):
            raise TypeError("expect Iterable, get", type(glob_regex))

    def get_db_location(self):
        """return the absolute path of the database"""
        return self._db_path

    def get_avail_entries(self):
        """get all available entries"""
        if self._available_entries is None:
            d = []
            for regex in self._glob:
                d.extend(str(x.relative_to(self._db_path)) for x in self._db_path.glob(regex))
            self._available_entries = d
        return self._available_entries

    def add_entry(self, entry: str, data_object, rewrite=False):
        """add a new entry to database with data_object as its content

        Args:
            entry (str) : name of entry
            data_object (any object with __str__ method)
        """
        entry_path = self._db_path / entry
        if not entry_path.exists() or rewrite:
            makedirs(entry_path.parent, exist_ok=True)
            with entry_path.open('w') as h:
                print(str(data_object), file=h)
            self._available_entries = None
        else:
            _logger.warning("Entry %s is found at %s. Skip", entry, str(entry_path))

    def filter(self, regex=None):
        """filter the database entries

        Args:
            regex (str): regular expression to filter

        Returns:
            tuple
        """
        filtered = []
        if regex is None:
            for i, e in enumerate(self.get_avail_entries()):
                filtered.append((i, e))
        else:
            for i, e in enumerate(self.get_avail_entries()):
                if search(regex, e) is not None:
                    filtered.append((i, e))
        return filtered

    def _get_entry(self, entry: Union[str, int], absolute: bool = False) -> Union[str, None]:
        """get the path of the database entry

        Args:
            entry (int or str)
            absolute (bool): if True, the absolute path will be returned

        Returns:
            string if entry is found, otherwise None
        """
        try:
            entry = int(entry)
            entry = self.get_avail_entries()[entry]
        except IndexError:
            return None
        except ValueError:
            pass

        path = self._db_path / entry
        if path.exists():
            if absolute:
                return str(path)
            return str(entry)
        return None

    def has_entry(self, entry: Union[str, int]) -> bool:
        """True if database has the entry ``entry``"""
        p = self._get_entry(entry)
        if p is None:
            return False
        return True

    def get_entry(self, entry: Union[str, int]) -> Union[str, None]:
        """get the name of the database entry

        Args:
            entry (int or str)

        Returns:
            string if entry is found, otherwise None
        """
        return self._get_entry(entry, False)

    def get_entry_path(self, entry: Union[str, int]) -> Union[str, None]:
        """get the absolute path to the database entry

        Args:
            entry (int or str)

        Returns:
            string if entry is found, otherwise None
        """
        return self._get_entry(entry, True)


class DBCell(_DBBase):
    """database of crystall structure cells"""
    avail_writers = list(Cell.avail_exporters) + ["w2k",]
    avail_readers = list(Cell.avail_readers) + ["w2k",]
    default_writer = "vasp"

    def __init__(self):
        _DBBase.__init__(self, "cell", ["**/*.json", "**/*.cif"])
        self.get_cell = self.get_entry
        self.get_cell_path = self.get_entry_path
        self.get_avail_cells = self.get_avail_entries

    def extract(self, cell_entry, filename=None, writer=None):
        """extract the entry from cell database"""
        self._write(self._reader(cell_entry), output_path=filename, writer=writer)

    def _reader(self, cell_entry: Union[str, int], reader=None):
        """read in an entry and return a cell object"""
        pcell = self.get_cell_path(cell_entry)
        if pcell is None:
            raise DBEntryNotFoundError("cell entry {} is not found".format(cell_entry))
        if reader is None:
            reader = detect(pcell, fail_with_ext=True)
        if reader in Cell.avail_readers:
            return Cell.read(pcell, form=reader)
        if reader == "w2k":
            return Struct.read(pcell)
        raise ValueError("unsupported format for reading cell: {}".format(reader))

    def _write(self, cell_object, output_path: Union[str, int] = None, writer=None):
        """write to some format"""
        if writer is None:
            if output_path is None:
                writer = self.default_writer
                _logger.debug("use default cell writer: %s", writer)
            else:
                writer = detect(output_path, fail_with_ext=True)
            if not writer:
                raise ValueError("fail to detect a format for writing cell")
        if isinstance(cell_object, Cell):
            if writer in Cell.avail_exporters:
                cell_object.write(writer, filename=output_path)
                return
            if writer == "w2k":
                Struct.from_cell(cell_object).write(filename=output_path)
                return
        elif isinstance(cell_object, Struct):
            if writer in Cell.avail_exporters:
                cell_object.get_cell().write(writer, filename=output_path)
                return
            if writer == "w2k":
                cell_object.write(filename=output_path)
                return
        raise ValueError("invalid class of input cell object: {}".format(type(cell_object)))


class DBWorkflow(_DBBase):
    """database of workflows"""

    def __init__(self):
        _DBBase.__init__(self, "workflow", ["*_*",])
        self._libs = self._db_path / "libs"
        self.get_workflow = self.get_entry
        self.get_workflow_path = self.get_entry_path
        self.get_avail_workflows = self.get_avail_entries

    def _init_workflow_libs_symlink(self, wf: Union[str, int]):
        """initialize symlinks to workflow lib shell file"""
        wf = self.get_workflow(wf)
        if wf is None:
            raise DBEntryNotFoundError("entry {} is not found".format(wf))
        p = self._db_path / wf / ".depends"
        if p.is_file():
            _logger.debug(p)
            with p.open() as f:
                for x in f.readlines():
                    dep = x.strip()
                    pnew = self._db_path / wf / dep
                    if pnew.is_symlink():
                        pnew.unlink()
                    pnew.symlink_to(self._libs / dep)
        else:
            prog = wf.split("_")[0] + ".sh"
            p = self._db_path / wf / prog
            _logger.debug(p)
            if p.is_symlink():
                p.unlink()
            p.symlink_to(self._libs / prog)

    def copy_workflow_to_dst(self, wf: Union[str, int], dst: str = ".",
                             overwrite: bool = False, copy_readme: bool = False):
        """copy the workflow files to destination

        Args:
            wf (str or int)
            dst (str)
            overwrite (bool)
            copy_readme (bool)
        """
        self._init_workflow_libs_symlink(wf)
        p = pathlib.Path(self.get_workflow_path(wf))
        dst = pathlib.Path(dst)
        if not dst.is_dir():
            raise ValueError("destination must be a directory")
        _logger.info("Copying %s files to %s", p.name, dst.name)
        for x in p.glob("*"):
            if x.name == "README.md" and not copy_readme:
                continue
            if not any([x.name.startswith("."), x.name.endswith(".log"), x.is_dir()]):
                f = dst / x.name
                if not f.is_file() or overwrite:
                    copy(x, f)
                    _logger.info(">> %s", f.name)
                else:
                    _logger.warning(">> %s found. Use --force to overwrite.", f.name)

class DBKPath(_DBBase):
    """database of k-point path"""

    def __init__(self):
        _DBBase.__init__(self, "kpath", ["**/*.json",])

