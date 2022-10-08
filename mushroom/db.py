# -*- coding: utf-8 -*-
"""database related"""
import pathlib
from re import search
from os import makedirs
import shutil
from collections.abc import Iterable
from typing import Union

from mushroom.core.pkg import detect
from mushroom.core.logger import create_logger
from mushroom.core.cell import Cell
from mushroom.core.typehint import Path
from mushroom.w2k import Struct

__all__ = [
        "DBCell",
        "DBWorkflow",
        "DBKPath",
        "DBDoctemp",
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
    def __init__(self, name: str, glob_regex: Iterable, excludes: Iterable = None,
                 dir_only: bool = False):
        name = pathlib.Path(name)
        if name.is_absolute():
            self._db_path = name
        else:
            self._db_path = mushroom_db_home / name
        self._excludes = []
        self._dir_only = dir_only
        if excludes is not None:
            for ex in excludes:
                self._excludes.extend(self._db_path.glob(ex))
        self._glob = glob_regex
        self._available_entries = None
        if not isinstance(glob_regex, Iterable):
            raise TypeError("expect Iterable, get", type(glob_regex))

    @property
    def N(self):
        """number of entries"""
        return len(self.get_avail_entries())

    def get_db_location(self):
        """return the absolute path of the database"""
        return self._db_path

    def get_avail_entries(self):
        """get all available entries"""
        if self._available_entries is None:
            d = []
            for regex in self._glob:
                d.extend(str(x.relative_to(self._db_path))
                         for x in self._db_path.glob(regex)
                         if x not in self._excludes and
                         not (self._dir_only and not x.is_dir()))
            # remove cwd
            if "." in d:
                i = d.index(".")
                del d[i]
            self._available_entries = d
        return self._available_entries

    def reload(self):
        """reload the list of entries"""
        self._available_entries = None

    def register(self, entry: Path,
                 relative: bool = False, overwrite: bool = False):
        """register a new entry to database

        Args:
            entry (str) : file name of entry
            relative (bool)
            overwrite (bool)

        Returns:
            str, the path to the entry if the entry does not exist or overwrite is switched on.
            None, otherwise.
        """
        entry_path = self._db_path / entry
        if not entry_path.exists() or overwrite:
            makedirs(entry_path.parent, exist_ok=True)
            if relative:
                entry_path = entry_path.relative_to(pathlib.Path('.').resolve())
            return str(entry_path)
        _logger.warning("Entry %s is found at %s. Skip", str(entry), str(entry_path))
        return None

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
    assert default_writer in avail_writers

    def __init__(self):
        _DBBase.__init__(self, "cell", ["**/*.json", "**/*.cif"])
        self.get_cell = self.get_entry
        self.get_cell_path = self.get_entry_path
        self.get_avail_cells = self.get_avail_entries
        self.read_format = None

    def _read_cell(self, pcell, reader=None, primitize=False, standardize=False, **kwargs):
        """read a cell file"""
        if reader is None:
            reader = detect(pcell, fail_with_ext=True)
        if reader not in self.avail_readers:
            raise ValueError("unsupported format for reading cell: {}".format(reader))
        if reader == "w2k":
            if primitize:
                raise NotImplementedError("primitive w2k format is not supported")
            return Struct.read(pcell, **kwargs)
        # will use the reader format as fallback when export format is unknown
        self.read_format = reader
        # default use Cell
        c = Cell.read(pcell, form=reader, **kwargs)
        if standardize:
            c = c.standardize(to_primitive=primitize)
        else:
            if primitize:
                c = c.primitize()
        return c

    def convert(self, pcell: Path, output_path=None, reader=None, writer=None,
                primitize=False, standardize=False):
        """convert a file in one format of lattice cell to another"""
        self._write(self._read_cell(pcell, reader=reader, primitize=primitize, standardize=False),
                    output_path=output_path, writer=writer)

    def extract(self, cell_entry: Union[str, int], output_path=None,
                reader=None, writer=None, primitize=False, standardize=False):
        """extract the entry from cell database"""
        pcell = self.get_cell_path(cell_entry)
        if pcell is None:
            raise DBEntryNotFoundError("cell entry {} is not found".format(cell_entry))
        self._write(self._read_cell(pcell, reader=reader, primitize=primitize, standardize=False),
                    output_path=output_path, writer=writer)

    def _write(self, cell_object, output_path: Union[str, int]=None,
               writer=None):
        """write to some format"""
        if writer is None:
            if output_path is None:
                writer = self.default_writer
                _logger.debug("use default cell writer: %s", writer)
            else:
                writer = detect(output_path)
            if not writer:
                _logger.debug("fail to detect a format for writing cell, fallback to reader: %s",
                              self.read_format)
                writer = self.read_format
        if isinstance(cell_object, Cell):
            if writer == "w2k":
                Struct.from_cell(cell_object).write(filename=output_path)
                return
            cell_object.write(writer, filename=output_path)
            return
        if isinstance(cell_object, Struct):
            if writer == "w2k":
                cell_object.write(filename=output_path)
                return
            cell_object.get_cell().write(writer, filename=output_path)
            return
        raise ValueError("invalid class of input cell object: {}".format(type(cell_object)))

class DBWorkflow(_DBBase):
    """database of workflows"""

    def __init__(self):
        _DBBase.__init__(self, "workflow", ["*_*",], dir_only=True)
        self._libs = self._db_path / "libs"
        self.get_workflow = self.get_entry
        self.get_workflow_path = self.get_entry_path
        self.get_avail_workflows = self.get_avail_entries

    def init_workflow_libs_symlink(self, wf: Union[str, int]):
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
            _logger.warning(".depends file is not found for workflow %s", wf)

    def copy_workflow(self, wf: Union[str, int], dst: str = ".", create_dir: bool = True,
                      overwrite: bool = False, copy_readme: bool = False):
        """copy the workflow files to destination

        Args:
            wf (str or int)
            dst (str)
            create_dir (bool): if set True, dst will be created when it is not found.
                Otherwise NotADirectoryError will be raised
            overwrite (bool)
            copy_readme (bool)
        """
        self.init_workflow_libs_symlink(wf)
        p = pathlib.Path(self.get_workflow_path(wf))
        dst = pathlib.Path(dst)
        if not dst.is_dir():
            try:
                if create_dir:
                    makedirs(dst)
                else:
                    raise NotADirectoryError("directory {} does not exist".format(dst))
            except PermissionError as err:
                raise PermissionError("cannot create directory due to limited permission") from err
            else:
                raise OSError("cannot create directory")
            _logger.info("Created directory under %s", str(dst))
        _logger.info("Copying %s files to %s", p.name, dst.name)
        for x in p.glob("*"):
            if x.name == "README.md" and not copy_readme:
                continue
            if not any([x.name.startswith("."), x.name.endswith(".log"), x.is_dir()]):
                f = dst / x.name
                if not f.is_file() or overwrite:
                    shutil.copy(x, f)
                    _logger.info(">> %s", f.name)
                else:
                    _logger.warning(">> %s found. Use --force to overwrite.", f.name)

class DBKPath(_DBBase):
    """database of k-point path"""

    def __init__(self):
        _DBBase.__init__(self, "kpath", ["**/*.json",])

class DBDoctemp(_DBBase):
    """database of document template"""

    def __init__(self):
        _DBBase.__init__(self, "doctemp", ["tex-*",], excludes=[".gitignore",".DS_Store"])
        self.get_doctemp = self.get_entry
        self.get_doctemp_path = self.get_entry_path

    # pylint: disable=R0912
    def copy_doctemp(self, dt: Union[str, int], dst: str = ".", create_dir: bool = True,
                     overwrite: bool = False):
        """copy the document template to destination

        Args:
            dt (str or int)
            dst (str)
            create_dir (bool): if set True, dst will be created when it is not found.
                Otherwise NotADirectoryError will be raised
            overwrite (bool)
        """
        p = pathlib.Path(self.get_doctemp_path(dt))
        dst = pathlib.Path(dst)
        if not dst.is_dir():
            try:
                if create_dir:
                    makedirs(dst)
                else:
                    raise NotADirectoryError("directory {} does not exist".format(dst))
            except PermissionError as err:
                raise PermissionError("cannot create directory due to limited permission") from err
            else:
                raise OSError("cannot create directory")
            _logger.info("Created directory under %s", str(dst))
        _logger.info("Copying %s files to %s", p.name, dst.name)
        if p.is_file():
            files = [p,]
        elif p.is_dir():
            files = list(p.glob("*"))
        else:
            raise TypeError("expected file/directory of document template, {}".format(p.name))
        _logger.info("> files found: %r", list(x.name for x in files))
        for x in files:
            if not any([x.name.startswith("."), x.name.endswith(".log")]):
                f = dst / x.name
                if not f.exists() or overwrite:
                    if x.is_file():
                        shutil.copy(x, f)
                    else:
                        shutil.copytree(x, f)
                    _logger.info(">> %s", f.name)
                else:
                    _logger.warning(">> %s found. Use --force to overwrite.", f.name)

