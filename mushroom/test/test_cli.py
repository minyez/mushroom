# -*- coding: utf-8 -*-
"""test the unified command line entry"""
import tempfile
import unittest as ut
from pathlib import Path

from click.testing import CliRunner

from mushroom.cli import main, SCRIPT_COMMANDS, SCRIPTS_DIR


class test_cli(ut.TestCase):

    def setUp(self):
        self.runner = CliRunner()

    def test_all_scripts_registered(self):
        registered = {script for _, cmds in SCRIPT_COMMANDS.values() for script in cmds.values()}
        existing = {p.name for p in SCRIPTS_DIR.glob("m_*")}
        self.assertEqual(registered, existing)

    def test_help(self):
        result = self.runner.invoke(main, ["-h"])
        self.assertEqual(result.exit_code, 0)
        for group in ("aims", "vasp", "detect", "fiteos"):
            self.assertIn(group, result.output)
        result = self.runner.invoke(main, ["aims", "-h"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("extract the band energies from aims output", result.output)

    def test_script_help_passthrough(self):
        result = self.runner.invoke(main, ["kpt", "kmesh", "-h"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("compute the k-point mesh of a k-grids", result.output)
        self.assertIn("--gamma-center", result.output)

    def test_detect(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            result = self.runner.invoke(main, ["detect", tmpdir])
            self.assertEqual(result.exit_code, 1)
            self.assertIn("no known calculation detected", result.output)
            for name in ("INCAR", "POSCAR", "KPOINTS"):
                (Path(tmpdir) / name).touch()
            result = self.runner.invoke(main, ["detect", tmpdir])
            self.assertEqual(result.exit_code, 0)
            self.assertIn("VASP", result.output)
            result = self.runner.invoke(main, ["detect", "-q", tmpdir])
            self.assertEqual(result.output, "vasp\n")


if __name__ == "__main__":
    ut.main()
