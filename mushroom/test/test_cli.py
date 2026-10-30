# -*- coding: utf-8 -*-
"""test the unified command line entry"""
import tempfile
import unittest as ut
from pathlib import Path

from click.testing import CliRunner

from mushroom.cli import main, SCRIPT_COMMANDS, SCRIPTS_DIR
from mushroom.cli._utils import expand_multi_values, fill_optional_values

AIMS_DATA = Path(__file__).resolve().parents[1] / "aims" / "test" / "data"
TEST_DATA = Path(__file__).resolve().parent / "data"


class test_cli(ut.TestCase):

    def setUp(self):
        self.runner = CliRunner()

    def test_all_scripts_registered(self):
        registered = {script for _, cmds in SCRIPT_COMMANDS.values() for script in cmds.values()}
        native = {"m_aims_check_ob_ortho"}
        native.update(p.name for p in SCRIPTS_DIR.glob("m_*")
                      if "deprecated" in p.read_text())
        existing = {p.name for p in SCRIPTS_DIR.glob("m_*")}
        self.assertEqual(registered | native, existing)

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


class test_expand_multi_values(ut.TestCase):

    def test_expand(self):
        flags = {"--compare", "-t"}
        cases = [
            (["a", "--compare", "b", "c", "-o", "d"],
             ["a", "--compare", "b", "--compare", "c", "-o", "d"]),
            (["--compare", "c", "b", "a"],
             ["--compare", "c", "--compare", "b", "--compare", "a"]),
            (["-t", "-1.5", "2", "--ef", "1"], ["-t", "-1.5", "-t", "2", "--ef", "1"]),
            (["-t", "a", "--", "b"], ["-t", "a", "--", "b"]),
            (["--", "-t", "a", "b"], ["--", "-t", "a", "b"]),
            (["--compare"], ["--compare"]),
            (["--compare=a", "b"], ["--compare=a", "b"]),
        ]
        for args, expected in cases:
            self.assertEqual(expand_multi_values(args, flags), expected)


class test_fill_optional_values(ut.TestCase):

    def test_fill(self):
        consts = {"-i": "geometry.in"}
        cases = [
            (["a", "-i"], ["a", "-i", "geometry.in"]),
            (["-i", "--vbmz"], ["-i", "geometry.in", "--vbmz"]),
            (["-i", "my.in", "a"], ["-i", "my.in", "a"]),
            (["-i", "--", "a"], ["-i", "geometry.in", "--", "a"]),
            (["--", "-i"], ["--", "-i"]),
        ]
        for args, expected in cases:
            self.assertEqual(fill_optional_values(args, consts), expected)


class test_aims_commands(ut.TestCase):

    def setUp(self):
        self.runner = CliRunner()
        self.band_out = str(AIMS_DATA / "Si_GW_band1001.out")
        self.aimsout = str(AIMS_DATA / "Si.pgw_band.aims.out")

    def invoke(self, *args):
        result = self.runner.invoke(main, ["aims", *args])
        self.assertIsNone(result.exception, msg=result.output)
        return result

    def test_gap(self):
        self.assertIn("gap", self.invoke("gap", self.band_out).output.lower())

    def test_dim(self):
        self.assertNotEqual(self.invoke("dim", self.aimsout).output, "")

    def test_exclusive_options(self):
        result = self.runner.invoke(main, ["aims", "band", self.band_out, "--vbmz", "--cbmz"])
        self.assertEqual(result.exit_code, 2)
        self.assertIn("mutually exclusive", result.output)

    def test_append_basis_requires_elements(self):
        result = self.runner.invoke(main, ["aims", "append-basis", "control.in", "any"])
        self.assertEqual(result.exit_code, 2)

    def test_optional_value_uses_const(self):
        with self.runner.isolated_filesystem():
            result = self.runner.invoke(main, ["aims", "band", self.band_out, "--data", "--sym-cf"])
            self.assertIsNone(result.exception, msg=result.output)
            # control.in is only read when plotting
            result = self.runner.invoke(main, ["aims", "band", self.band_out, "--sym-cf"])
            self.assertIsInstance(result.exception, FileNotFoundError)
            self.assertIn("control.in", str(result.exception))

    def test_get_input(self):
        with self.runner.isolated_filesystem():
            self.assertIn("Writing control.in", self.invoke("get-input", self.aimsout).output)
            self.assertTrue(Path("control.in").exists())
            self.assertTrue(Path("geometry.in").exists())
            self.assertIn("exists, skip", self.invoke("get-input", self.aimsout).output)
            self.assertIn("Overwriting", self.invoke("get-input", self.aimsout, "-f").output)


class test_vasp_commands(ut.TestCase):

    POSCAR = "Cu\n3.6\n0 .5 .5\n.5 0 .5\n.5 .5 0\nCu\n1\nDirect\n0 0 0\n"

    def setUp(self):
        self.runner = CliRunner()

    def invoke(self, *args):
        result = self.runner.invoke(main, ["vasp", *args])
        self.assertIsNone(result.exception, msg=result.output)
        return result

    def test_gap(self):
        output = self.invoke("gap", "-v", str(TEST_DATA / "EIGENVAL_1")).output
        self.assertIn("gap", output.lower())

    def test_band(self):
        with self.runner.isolated_filesystem():
            Path("POSCAR").write_text(self.POSCAR)
            self.invoke("band", "-v", str(TEST_DATA / "EIGENVAL_1"), "--vbmz", "--sym", "G", "X", "L")
            self.assertTrue(Path("plotband.agr").exists())

    def test_band_exclusive_options(self):
        result = self.runner.invoke(main, ["vasp", "band", "--ferz", "--vbmz"])
        self.assertEqual(result.exit_code, 2)
        self.assertIn("mutually exclusive", result.output)

    def test_chg(self):
        with self.runner.isolated_filesystem():
            Path("CHGCAR").write_bytes((TEST_DATA / "CHGCAR_1.vasp").read_bytes())
            self.invoke("chg")
            self.assertTrue(Path("CHGCAR.cube").exists())

    def test_pwav(self):
        with self.runner.isolated_filesystem():
            Path("POSCAR").write_text(self.POSCAR)
            self.invoke("pwav", "-p", str(TEST_DATA / "PROCAR_1"), "--apb", "1:s:1,2", "1:p:3")
            self.assertTrue(Path("plotpwav.agr").exists())
            self.assertEqual(Path("pwav.dat").read_text().count("#atom-projector-band"), 2)


if __name__ == "__main__":
    ut.main()
