#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""testing database related facilities"""
import unittest as ut
import os
import tempfile
import pathlib

from mushroom.db import PlainTextDB
from mushroom.db import DBCell, DBWorkflow, DBEntryNotFoundError, DBDoctemp
from mushroom.w2k import Struct

try:
    force_copy = os.environ["FORCE_COPY"]
    force_copy = True
except KeyError:
    force_copy = False


class test_plaintextdb(ut.TestCase):
    """test the base class"""

    def test_init(self):
        self.assertRaises(TypeError, PlainTextDB, None, "**/filename")
        ptdb = PlainTextDB("relapath", ["**/filename",])
        ptdb = PlainTextDB("/abspath", ["**/filename",])
        ptdb = PlainTextDB("/abspath", "**/filename")
        # raise for non-iterable glob
        self.assertRaises(TypeError, PlainTextDB, "relapath", 1)


class test_initialize_internal(ut.TestCase):
    """test initialization of internal database"""

    def test_dbcell(self):
        """cell database"""
        dbc = DBCell()
        self.assertFalse(dbc.has_entry("entry not exist"))
        self.assertListEqual([], dbc.filter(r"no entry match this"))
        self.assertIsNone(dbc.get_entry_path("entry not exist"))

    def test_dbworkflow(self):
        """cell database"""
        dbwf = DBWorkflow()
        self.assertFalse(dbwf.has_entry("entry not exist"))
        self.assertListEqual([], dbwf.filter(r"no entry match this"))
        self.assertIsNone(dbwf.get_entry_path("entry not exist"))
        if not force_copy:
            return
        # test copy a workflow to temprary directory
        for i in range(dbwf.N):
            with tempfile.TemporaryDirectory() as td:
                dbwf.copy_workflow(i, dst=td)

    def test_dbdoctemp(self):
        """cell database"""
        dbdt = DBDoctemp()
        self.assertFalse(dbdt.has_entry("entry not exist"))
        self.assertListEqual([], dbdt.filter(r"no entry match this"))
        self.assertIsNone(dbdt.get_entry_path("entry not exist"))
        if not force_copy:
            return
        # test copy a doctemp to temprary directory
        for i in range(dbdt.N):
            with tempfile.TemporaryDirectory() as td:
                dbdt.copy_doctemp(i, dst=td)


class test_dbcell(ut.TestCase):
    """test methods of cell database instance"""

    dbc = DBCell()

    def test_register_new_cell(self):
        """register new cell entry"""
        if self.dbc.N > 0:
            entry = self.dbc.get_cell(0)
            self.assertIsNone(self.dbc.register(entry), None)
            self.assertIsNone(self.dbc.register(entry))
            self.assertEqual(self.dbc.register(entry, overwrite=True),
                             os.path.join(self.dbc._db_path, entry))


if __name__ == "__main__":
    ut.main()
