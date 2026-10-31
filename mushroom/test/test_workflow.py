#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test workflow utilities"""
import os
import pathlib
import subprocess as sp
import sys
import tempfile
import unittest as ut
from unittest import mock

from mushroom import workflow


class test_utilities(ut.TestCase):
    """test simple utilities"""

    def test_get_ntasks(self):
        """the scheduler variable has the priority"""
        with mock.patch.dict(os.environ, {"SLURM_NTASKS": "16"}):
            self.assertEqual(workflow.get_ntasks(4), 16)
        with mock.patch.dict(os.environ, clear=True):
            self.assertEqual(workflow.get_ntasks(4), 4)

    def test_largest_div_below_sqrt(self):
        """check some integers"""
        for num, div in ((1, 1), (4, 2), (7, 1), (12, 3), (36, 6), (48, 6)):
            self.assertEqual(workflow.largest_div_below_sqrt(num), div)

    def test_require(self):
        """raise when missing"""
        self.assertRaises(FileNotFoundError, workflow.require_files, __file__, "no_such_file")
        workflow.require_executable(sys.executable)
        self.assertRaises(FileNotFoundError, workflow.require_executable, "no_such_command")


class test_run_command(ut.TestCase):
    """test running commands"""

    def test_redirect_and_failure(self):
        """both stdout and stderr go to the file, and failure raises"""
        code = "import sys; print('out'); print('err', file=sys.stderr, flush=True); sys.exit({})"
        with tempfile.TemporaryDirectory() as tmpdir:
            workflow.run_command([sys.executable, "-c", code.format(0)], "o", cwd=tmpdir)
            lines = (pathlib.Path(tmpdir) / "o").read_text().split()
            self.assertEqual(sorted(lines), ["err", "out"])
            self.assertRaises(sp.CalledProcessError, workflow.run_command,
                              [sys.executable, "-c", code.format(1)], "o", cwd=tmpdir)


if __name__ == '__main__':
    ut.main()
