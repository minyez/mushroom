# -*- coding: utf-8 -*-
"""database related"""
import pathlib
from re import search
from os import makedirs
from shutil import copy
from collections.abc import Iterable
from mushroom.core.logger import create_logger

_logger = create_logger("db")
del create_logger

# database directory of mushroom
mushroom_db_home = pathlib.Path(__file__).parent.parent.parent / "db"

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
    def __init__(self, name: str, glob_regex: Iterable = None):
        name = pathlib.Path(name)
        if name.is_absolute():
            self._db_path = name
        else:
            self._db_path = mushroom_db_home / name
        self._glob = glob_regex
        self._available_entries = None
        if glob_regex is None:
            self._glob = ["**/*.json"]
        else:
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

    def has_entry(self, entry: str) -> bool:
        """True if database has the entry ``entry``"""
        if entry in self.get_avail_entries():
            return True
        return False

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

    def get_entry(self, entry):
        """get the name of the database entry

        Args:
            entry (int or str)

        Returns:
            string if entry is found, otherwise None
        """
        try:
            entry = int(entry)
            entry = self.get_avail_entries()[entry]
        except ValueError:
            pass

        path = self._db_path / entry
        if path.exists():
            return str(entry)
        return None

    def get_entry_path(self, entry):
        """get the absolute path to the database entry

        Args:
            entry (int or str)

        Returns:
            string if entry is found, otherwise None
        """
        try:
            entry = int(entry)
            entry = self.get_avail_entries()[entry]
        except ValueError:
            pass

        entry = self._db_path / entry
        if entry.exists():
            return str(entry)
        return None


class DBCell(_DBBase):
    """database of crystall structure cells"""

    def __init__(self):
        _DBBase.__init__(self, "cell", ["**/*.json", "**/*.cif"])

class DBWorkflow(_DBBase):
    """database of workflows"""

    def __init__(self):
        _DBBase.__init__(self, "workflow", ["*_*",])
        self._libs = self._db_path / "libs"
        self.get_workflow = self.get_entry
        self.get_workflow_path = self.get_entry_path
        self.get_avail_workflows = self.get_avail_entries

    def init_workflow_libs_symlink(self, wf: str):
        """initialize symlinks to workflow lib shell file"""
        if not self.has_entry(wf):
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

    def copy_workflow_to_dst(self, wf, dst: str = ".",
                             overwrite: bool = False, copy_readme: bool = False):
        """copy the workflow files to destination

        Args:
            wf (str or int)
            dst (str)
            overwrite (bool)
            copy_readme (bool)
        """
        p = pathlib.Path(self.get_entry_path(wf))
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

