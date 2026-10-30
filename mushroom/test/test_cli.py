# -*- coding: utf-8 -*-
"""test the unified command line entry"""
import tempfile
import unittest as ut
from pathlib import Path

from click.testing import CliRunner

from mushroom.cli import main, SCRIPT_COMMANDS, SCRIPTS_DIR
from mushroom.cli._utils import expand_multi_values, fill_optional_values
from mushroom.cli.cell import _READERS, _WRITERS
from mushroom.cli.gap import _EPS_KINDS
from mushroom.gap import Eps
from mushroom.io import CellIO

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

    def test_dos(self):
        """total dos is summed over spins, and projectors can be given by index"""
        with self.runner.isolated_filesystem():
            Path("POSCAR").write_text(self.POSCAR)
            self.invoke("dos", "-d", str(TEST_DATA / "DOSCAR_2"), "--ap", "Cu:0", "Cu:1,2,3")
            self.assertTrue(Path("plotpdos.agr").exists())
            tdos_lines = Path("tdos.dat").read_text().splitlines()
            self.assertEqual(len(tdos_lines), 302)
            self.assertEqual(len(tdos_lines[1].split()), 2)
            self.assertEqual(Path("pdos.dat").read_text().count("#atom-projector"), 2)

    def test_pwav(self):
        with self.runner.isolated_filesystem():
            Path("POSCAR").write_text(self.POSCAR)
            self.invoke("pwav", "-p", str(TEST_DATA / "PROCAR_1"), "--apb", "1:s:1,2", "1:p:3")
            self.assertTrue(Path("plotpwav.agr").exists())
            self.assertEqual(Path("pwav.dat").read_text().count("#atom-projector-band"), 2)


class test_w2k_commands(ut.TestCase):

    def setUp(self):
        self.runner = CliRunner()

    def invoke(self, *args):
        result = self.runner.invoke(main, ["w2k", *args])
        self.assertIsNone(result.exception, msg=result.output)
        return result

    @staticmethod
    def copy_case():
        for suffix in ("struct", "energy", "in1"):
            Path(f"1.{suffix}").write_bytes((TEST_DATA / f"1.{suffix}").read_bytes())

    def test_gap(self):
        with self.runner.isolated_filesystem():
            self.copy_case()
            self.assertIn("gap", self.invoke("gap", "-u", "ry").output.lower())

    def test_band(self):
        with self.runner.isolated_filesystem():
            self.copy_case()
            self.invoke("band", "--vbmz", "--sym", "G", "X", "L", "-o", "b.agr")
            self.assertTrue(Path("b.agr").exists())

    def test_band_exclusive_options(self):
        result = self.runner.invoke(main, ["w2k", "band", "--ferz", "--vbmz"])
        self.assertEqual(result.exit_code, 2)
        self.assertIn("mutually exclusive", result.output)

    def test_dos(self):
        """total dos can be plotted, and pdos is exported with atoms from struct"""
        lines = ["# title", "# fermi", "# ENERGY TOTAL 1:s 2:s"]
        lines.extend(f"{i - 5}.0 1.0 0.1 0.2" for i in range(11))
        with self.runner.isolated_filesystem():
            self.copy_case()
            Path("1.dos1ev").write_text("\n".join(lines) + "\n")
            self.invoke("dos", "-d", "1.dos1ev", "--ap", "Ti:s", "C:s")
            self.assertTrue(Path("plotpdos.agr").exists())
            self.assertEqual(Path("pdos.dat").read_text().count("#atom-projector"), 2)

    def test_dos_requires_dosfile(self):
        result = self.runner.invoke(main, ["w2k", "dos"])
        self.assertEqual(result.exit_code, 2)


class test_gap_commands(ut.TestCase):

    def setUp(self):
        self.runner = CliRunner()

    def invoke(self, *args):
        result = self.runner.invoke(main, ["gap", *args])
        self.assertIsNone(result.exception, msg=result.output)
        return result

    def test_eps_kinds(self):
        self.assertEqual(_EPS_KINDS, Eps.known_kind)

    def test_analyze_eqpev(self):
        output = self.invoke("analyze-eqpev", "-f", str(TEST_DATA / "diamond_1.eqpeV_GW")).output
        self.assertIn("G0W0 band structure", output)

    def test_degw(self):
        with self.runner.isolated_filesystem():
            self.invoke("degw", "-e", str(TEST_DATA / "diamond_1.eqpeV_GW"), "-o", "d.dat")
            self.assertTrue(Path("d.dat").read_text().startswith("# "))

    def test_degw_requires_input(self):
        self.assertEqual(self.runner.invoke(main, ["gap", "degw"]).exit_code, 2)

    def test_eps(self):
        output = self.invoke("eps", str(TEST_DATA / "diamond.eps-q1"), "-n", "4", "-w", "2").output
        self.assertIn("E_macro", output)

    def test_eps_plot_requires_iomega(self):
        result = self.runner.invoke(main, ["gap", "eps", "any.eps-q1", "--plot"])
        self.assertEqual(result.exit_code, 2)

    def test_vmat(self):
        output = self.invoke("vmat", str(TEST_DATA / "1_diamond_q1.vmat"), "-s", "-20").output
        self.assertIn("matrix size = 143", output)


class test_cell_kpt_commands(ut.TestCase):

    POSCAR = ("Si\n1.0\n0 2.7 2.7\n2.7 0 2.7\n2.7 2.7 0\nSi\n2\nCartesian\n"
              "0 0 0\n1.35 1.35 1.35\n")

    def setUp(self):
        self.runner = CliRunner()

    def invoke(self, *args):
        result = self.runner.invoke(main, list(args))
        self.assertIsNone(result.exception, msg=result.output)
        return result

    def test_cell_formats(self):
        self.assertEqual(list(_READERS), CellIO.avail_readers)
        self.assertEqual(list(_WRITERS), CellIO.avail_writers)

    def test_convert(self):
        with self.runner.isolated_filesystem():
            Path("POSCAR").write_text(self.POSCAR)
            self.invoke("cell", "convert", "-I", "POSCAR", "-o", "aims", "-O", "geometry.in")
            self.assertEqual(Path("geometry.in").read_text().count("atom_frac"), 2)

    def test_convert_supercell(self):
        with self.runner.isolated_filesystem():
            Path("POSCAR").write_text(self.POSCAR)
            self.invoke("cell", "convert", "-I", "POSCAR", "--sc", "2", "2", "1", "-O", "sc.vasp")
            self.assertEqual(Path("transformation_matrix.dat").read_text(),
                             "2 0 0\n0 2 0\n0 0 1\n")
            self.assertEqual(len(Path("unfolding_map.dat").read_text().split()), 8)

    def test_convert_exclusive_and_required(self):
        args = ["cell", "convert"]
        self.assertEqual(self.runner.invoke(main, args).exit_code, 2)
        args += ["-I", "POSCAR", "-c", "0"]
        self.assertEqual(self.runner.invoke(main, args).exit_code, 2)

    def test_cell_database(self):
        self.assertIn("AgBr", self.invoke("cell", "convert", "-f", "AgBr").output)

    def test_info(self):
        with self.runner.isolated_filesystem():
            Path("POSCAR").write_text(self.POSCAR)
            self.assertIn("Fd-3m (#227)", self.invoke("cell", "info", "POSCAR", "-r", "-s").output)

    def test_kmesh(self):
        self.assertEqual(len(self.invoke("kpt", "kmesh", "2", "2", "2").output.splitlines()), 8)

    def test_kmesh_irreducible(self):
        with self.runner.isolated_filesystem():
            Path("POSCAR").write_text(self.POSCAR)
            output = self.invoke("kpt", "kmesh", "2", "2", "2", "--ir", "-I", "POSCAR").output
            self.assertIn("->", output)
        self.assertEqual(self.runner.invoke(main, ["kpt", "kmesh", "2", "2", "2", "--ir"]).exit_code, 2)


if __name__ == "__main__":
    ut.main()
