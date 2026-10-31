#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test workflow utilities"""
import os
import pathlib
import subprocess as sp
import sys
import tarfile
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

    def test_get_npar_kpar(self):
        """the product is the number of tasks"""
        self.assertTupleEqual(workflow.get_npar_kpar(6), (3, 2))
        self.assertTupleEqual(workflow.get_npar_kpar(1), (1, 1))

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


class test_stack_limit(ut.TestCase):
    """test running a command at the hard stack limit"""

    def test_wrapped_command(self):
        """the soft limit of the child process is the hard limit"""
        code = "import resource; s, h = resource.getrlimit(resource.RLIMIT_STACK); print(s == h)"
        output = sp.run(workflow.with_hard_stack_limit([sys.executable, "-c", code]),
                        capture_output=True, text=True, check=True).stdout
        self.assertEqual(output.strip(), "True")


class test_run_command_stderr(ut.TestCase):
    """test writing stderr to its own file"""

    def test_error_file(self):
        """stdout and stderr go to different files"""
        code = "import sys; print('out'); print('err', file=sys.stderr)"
        with tempfile.TemporaryDirectory() as tmpdir:
            workflow.run_command([sys.executable, "-c", code], "o", cwd=tmpdir, error="e")
            self.assertEqual((pathlib.Path(tmpdir) / "o").read_text(), "out\n")
            self.assertEqual((pathlib.Path(tmpdir) / "e").read_text(), "err\n")


class test_run_command_stdin(ut.TestCase):
    """test sending text to a command"""

    def test_stdin(self):
        """the text reaches standard input"""
        code = "import sys; print(sys.stdin.read().upper())"
        with tempfile.TemporaryDirectory() as tmpdir:
            workflow.run_command([sys.executable, "-c", code], "o", cwd=tmpdir, stdin="abc\n")
            self.assertEqual((pathlib.Path(tmpdir) / "o").read_text().strip(), "ABC")


class test_example(ut.TestCase):
    """test utilities to check against the example"""

    def test_open_and_diff(self):
        """files are extracted, and different files are found"""
        with tempfile.TemporaryDirectory() as tmpdir:
            top = pathlib.Path(tmpdir)
            (top / "example").mkdir()
            (top / "other").mkdir()
            for d, value in (("example", "1"), ("other", "1")):
                (top / d / "same").write_text(value)
            (top / "example" / "changed").write_text("1")
            (top / "other" / "changed").write_text("2")
            with tarfile.open(top / "example.tar.gz", "w:gz") as h:
                h.add(top / "example", arcname="example")
            with workflow.open_example(top / "example.tar.gz") as example:
                self.assertListEqual(
                    workflow.diff_files(example, top / "other", ["same", "changed"]), ["changed"])
            self.assertFalse(example.exists())


if __name__ == '__main__':
    ut.main()
