#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""testing database related facilities"""
import unittest as ut
import os
import tempfile
import pathlib
from mushroom.db import DBCell, DBWorkflow, DBEntryNotFoundError, DBDoctemp
from mushroom.w2k import Struct

try:
    force_copy = os.environ["FORCE_COPY"]
    force_copy = True
except KeyError:
    force_copy = False


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
        if force_copy:
            return
        # test copy a doctemp to temprary directory
        for i in range(dbdt.N):
            with tempfile.TemporaryDirectory() as td:
                dbdt.copy_doctemp(i, dst=td)


class test_dbcell(ut.TestCase):
    """test methods of cell database instance"""

    dbc = DBCell()

    def test_extract_raise(self):
        """test extracting cell entry"""
        if self.dbc.N > 0:
            self.assertRaises(ValueError, self.dbc.extract, 0, writer="unknown reader")
        self.assertRaises(DBEntryNotFoundError, self.dbc.extract, "unknown cell sample")

    def test_convert(self):
        """test the write functionality"""
        tf = tempfile.NamedTemporaryFile(suffix="_no_ext.")
        structfile = pathlib.Path(__file__).parent / "data" / "1.struct"
        self.dbc.convert(structfile, output_path=tf.name, writer='w2k')
        self.dbc.convert(structfile, output_path=tf.name, writer='vasp')
        tf.close()

    def test_extract_to_vasp(self):
        """successful extract"""
        tf = tempfile.NamedTemporaryFile(suffix=".POSCAR")
        if not force_copy:
            tf.close()
            return
        for i in range(self.dbc.N):
            with open(tf.name, 'w') as h:
                self.dbc.extract(i, output_path=h)
        tf.close()

    def test_extract_to_w2k(self):
        """successful extract"""
        tf = tempfile.NamedTemporaryFile(suffix=".struct")
        if not force_copy:
            tf.close()
            return
        for i in range(self.dbc.N):
            with open(tf.name, 'w') as h:
                self.dbc.extract(i, output_path=h)
        tf.close()

    def test_register_new_cell(self):
        """register new cell entry"""
        if self.dbc.N > 0:
            entry = self.dbc.get_cell(0)
            self.assertIsNone(self.dbc.register(entry))
            self.assertEqual(self.dbc.register(entry, overwrite=True),
                             os.path.join(self.dbc._db_path, entry))


if __name__ == "__main__":
    ut.main()
