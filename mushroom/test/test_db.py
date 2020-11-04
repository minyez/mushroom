#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""testing database related facilities"""
import unittest as ut
import tempfile
import os
import sys
from mushroom.db import DBCell, DBWorkflow

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



if __name__ == "__main__":
    ut.main()
