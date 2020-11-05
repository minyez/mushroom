#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""testing database related facilities"""
import unittest as ut
import tempfile
from mushroom.db import DBCell, DBWorkflow, DBEntryNotFoundError

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
        # test copy a workflow to temprary directory
        with tempfile.TemporaryDirectory() as td:
            dbwf.copy_workflow_to_dst(0, dst=td)

class test_dbcell(ut.TestCase):
    """test methods of cell database instance"""

    dbc = DBCell()

    def test_extract_raise(self):
        """test extracting cell entry"""
        self.assertRaises(ValueError, self.dbc.extract, 0, writer="unknown reader")
        self.assertRaises(DBEntryNotFoundError, self.dbc.extract, "unknown cell sample")

    def test_extract_to_vasp(self):
        """successful extract"""
        tf = tempfile.NamedTemporaryFile(suffix=".POSCAR")
        with open(tf.name, 'w') as h:
            self.dbc.extract(0, output_path=h)
        tf.close()

    def test_extract_to_w2k(self):
        """successful extract"""
        tf = tempfile.NamedTemporaryFile(suffix=".struct")
        with open(tf.name, 'w') as h:
            self.dbc.extract(0, output_path=h)
        tf.close()

if __name__ == "__main__":
    ut.main()
