# -*- coding: utf-8 -*-
"""database related"""
import pathlib
from re import search
from os import makedirs
import shutil
from collections.abc import Iterable
from typing import Union

from mushroom.core.logger import loggers
from mushroom.core.typehint import Path
from mushroom.io import CellIO

__all__ = [
    "DBCell",
    "DBWorkflow",
    "DBKPath",
    "DBDoctemp",
]

_logger = loggers["db"]

# database directory of mushroom
mushroom_db_home = pathlib.Path(__file__).parent.parent / "db"

if not mushroom_db_home.is_dir():
    raise FileNotFoundError("database directory is not found", mushroom_db_home.name)


class DBEntryNotFoundError(FileNotFoundError):
    """exception for failing to find database entry"""


class PlainTextDB:
    """base object for plain text database searching

    Args:
        name (str) : relative path for databse in mushroom. otherwise
        glob_regex (str or Iterable)
    """

    def __init__(self, dbpath: str, glob_regex: Iterable, excludes: Iterable = None,
                 dir_only: bool = False):
        try:
            dbpath = pathlib.Path(dbpath)
        except TypeError as e:
            raise TypeError("Invalid path for database: {}".format(dbpath)) from e

        if dbpath.is_absolute():
            self._db_path = dbpath
        else:
            self._db_path = mushroom_db_home / dbpath
        self._excludes = []
        self._dir_only = dir_only
        if excludes is not None:
            for ex in excludes:
                self._excludes.extend(self._db_path.glob(ex))
        if isinstance(glob_regex, str):
            self._glob = [glob_regex,]
        elif isinstance(glob_regex, Iterable):
            self._glob = glob_regex
        else:
            raise TypeError("expect str or other Iterable, get", type(glob_regex))
        self._available_entries = None

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
        if entry is None:
            _logger.warning("None Entry is parsed, skip")
            return None
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
        return p is not None

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


class DBCell(PlainTextDB):
    """database of crystall structure cells"""

    def __init__(self, db_cell_path: str = None):
        if db_cell_path is None:
            try:
                from mushroom.__config__ import db_cell_path
            except ImportError:
                pass
        if db_cell_path is None:
            db_cell_path = "cell"
        PlainTextDB.__init__(self, db_cell_path, ["**/*.json", "**/*.cif"])

    get_cell = PlainTextDB.get_entry
    get_cell_path = PlainTextDB.get_entry_path
    get_avail_cells = PlainTextDB.get_avail_entries


class DBWorkflow(PlainTextDB):
    """database of workflows"""

    def __init__(self):
        PlainTextDB.__init__(self, "workflow", ["*_*", ], dir_only=True)
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


class DBKPath(PlainTextDB):
    """database of k-point path"""

    def __init__(self):
        PlainTextDB.__init__(self, "kpath", ["**/*.json", ])


class DBDoctemp(PlainTextDB):
    """database of document template"""

    def __init__(self):
        PlainTextDB.__init__(self, "doctemp", ["tex-*", ], excludes=[".gitignore", ".DS_Store"])
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
            files = [p, ]
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
