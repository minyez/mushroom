# -*- coding: utf-8 -*-
"""database related"""
import pathlib
from re import search
from os import makedirs
from collections.abc import Iterable
from mushroom.core.logger import create_logger

_logger = create_logger("db")
del create_logger

# database directory of mushroom
mushroom_db_home = pathlib.Path(__file__).parent.parent.parent / "db"

if not mushroom_db_home.is_dir():
    raise FileNotFoundError("database directory is not found", mushroom_db_home.name)

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
            entry (str)
            data_object (any object with __str__ method)
        """
        entry_path = self._db_path / entry
        if not entry_path.is_file() or rewrite:
            makedirs(entry_path.parent, exist_ok=True)
            with open(entry_path, 'w') as h:
                print(str(data_object), file=h)
        else:
            _logger.warning("Entry %s is found at %s. Skip", entry, str(entry_path))

    def filter(self, regex):
        """filter the database entries

        Args:
            regex (str): regular expression to filter

        Returns:
            tuple
        """
        filtered = []
        for i, e in enumerate(self.get_avail_entries()):
            if search(regex, e) is not None:
                filtered.append((i, e))
        return filtered

    def get_entry(self, entry):
        """get the file path to the database entry

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
        if entry.is_file():
            return str(entry)
        return None


class DBCell(_DBBase):
    """database of crystall structure cells"""

    def __init__(self):
        _DBBase.__init__(self, "cell", ["**/*.json", "**/*.cif"])

