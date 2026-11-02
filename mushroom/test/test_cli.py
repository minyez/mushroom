# -*- coding: utf-8 -*-
"""test the unified command line entry"""
import os
import re
import tempfile
import unittest as ut
from pathlib import Path
from unittest.mock import MagicMock, patch

import click
import numpy as np
from click.testing import CliRunner

from mushroom.cli import main
from mushroom.cli._utils import expand_multi_values, fill_optional_values
from mushroom.cli.cell import _READERS, _WRITERS
from mushroom.cli.gap import _EPS_KINDS
from mushroom.cli.tools import _AVAILABLE_EOS
from mushroom.cli.w2k import _plot_pwav
from mushroom.core.eos import available_eos
from mushroom.gap import Eps
from mushroom.io import CellIO

AIMS_DATA = Path(__file__).resolve().parents[1] / "aims" / "test" / "data"
TEST_DATA = Path(__file__).resolve().parent / "data"


class test_cli(ut.TestCase):

    def setUp(self):
        self.runner = CliRunner()

    def test_deprecated_scripts_forward_to_commands(self):
        scripts_dir = Path(__file__).resolve().parents[2] / "scripts"
        scripts = [p for p in scripts_dir.glob("m_*") if p.name != "m_aims_check_ob_ortho"]
        self.assertGreater(len(scripts), 0)
        for script in scripts:
            matched = re.search(r"run_deprecated\((.*)\)", script.read_text())
            self.assertIsNotNone(matched, msg=script.name)
            command = main
            for name in re.findall(r'"([^"]+)"', matched.group(1)):
                command = command.commands[name]
            self.assertIsInstance(command, click.Command, msg=script.name)

    def test_help(self):
        result = self.runner.invoke(main, ["-h"])
        self.assertEqual(result.exit_code, 0)
        for group in ("aims", "vasp", "detect", "fiteos"):
            self.assertIn(group, result.output)
        result = self.runner.invoke(main, ["aims", "-h"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("extract the band energies from aims output", result.output)

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

    def test_dos_projector_names(self):
        """shell name in --ap is the sum of its orbitals, and unknown names are rejected"""
        with self.runner.isolated_filesystem():
            Path("POSCAR").write_text(self.POSCAR)
            doscar = str(TEST_DATA / "DOSCAR_2")
            self.invoke("dos", "-d", doscar, "--ap", "Cu:p", "Cu:px,py,pz")
            shell, orbitals = Path("pdos.dat").read_text().strip().split("#atom-projector:")[1:]
            shell = shell.strip().splitlines()[1:]
            self.assertEqual(shell, orbitals.strip().splitlines()[1:])
            self.assertTrue(any(float(l.split()[1]) > 0 for l in shell))
            result = self.runner.invoke(main, ["vasp", "dos", "-d", doscar, "--ap", "Cu:xyz"])
            self.assertIsInstance(result.exception, ValueError)

    def test_pwav_projector_names(self):
        """s weight of the lowest band in PROCAR_1 is nonzero, and unknown atoms are rejected"""
        with self.runner.isolated_filesystem():
            Path("POSCAR").write_text(self.POSCAR)
            procar = str(TEST_DATA / "PROCAR_1")
            self.invoke("pwav", "-p", procar, "--apb", "Cu:s:0")
            values = [float(l) for l in Path("pwav.dat").read_text().split("\n")[1:] if l]
            self.assertGreater(max(values), 0.0)
            result = self.runner.invoke(main, ["vasp", "pwav", "-p", procar, "--apb", "1:s:0"])
            self.assertIsInstance(result.exception, ValueError)

    def test_band_energy_range(self):
        with self.runner.isolated_filesystem():
            Path("POSCAR").write_text(self.POSCAR)
            self.invoke("band", "-v", str(TEST_DATA / "EIGENVAL_1"), "-e", "m8~5")
            world = re.search(r"@\s+world (.*)", Path("plotband.agr").read_text()).group(1)
            self.assertEqual(float(world.split(",")[1]), -8.0)
            self.assertEqual(float(world.split(",")[3]), 5.0)

    def test_pwav(self):
        with self.runner.isolated_filesystem():
            Path("POSCAR").write_text(self.POSCAR)
            self.invoke("pwav", "-p", str(TEST_DATA / "PROCAR_1"), "--apb", "Cu:s:1,2", "Cu:p:3")
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

    def test_band_without_symbols(self):
        with self.runner.isolated_filesystem():
            self.copy_case()
            self.invoke("band")
            self.assertTrue(Path("plotband.agr").exists())

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

    def test_band_invalid_energy_range(self):
        with self.runner.isolated_filesystem():
            self.copy_case()
            result = self.runner.invoke(main, ["w2k", "band", "-e", "bad"])
            self.assertIsInstance(result.exception, ValueError)
            self.assertIn("invalid energy range: bad", str(result.exception))

    def test_plot_pwav_scales_symbols(self):
        """symbol size follows weight, or its square root with prop_area"""
        pwav = np.array([[[4.0, 9.0]]])
        eigen = np.array([[[1.0, 2.0]]])
        bs = MagicMock()
        bs.get_pwav.return_value = pwav
        bs.get_eigen.return_value = eigen
        for prop_area, expected in [(False, [[8.0], [18.0]]), (True, [[4.0], [6.0]])]:
            graph = MagicMock()
            _plot_pwav(graph, [0.0], bs, ["Si:s:1"], 0, 0.5, 2.0, colors=["red"], prop_area=prop_area)
            args, kwargs = graph.plot.call_args
            np.testing.assert_allclose(args[1], [[0.5], [1.5]])
            np.testing.assert_allclose(kwargs["size"], expected)
            self.assertEqual((kwargs["color"], kwargs["label"]), ("red", "Si-s"))

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

    def test_eps_diff(self):
        with self.runner.isolated_filesystem():
            peps = str(TEST_DATA / "diamond.eps-q1")
            self.invoke("eps", peps, "-n", "4", "-w", "1", "--plot", "--diff", peps)
            self.assertTrue(Path("eps_iq_1_iomega_1.png").exists())

    def test_analyze_eqpev_from_case(self):
        with self.runner.isolated_filesystem():
            Path("diamond.struct").write_bytes((TEST_DATA / "1.struct").read_bytes())
            for src, dst in [("diamond_1.eqpeV_GW", "diamond.eqpeV_GW"),
                             ("diamond_2.eqpeV_GW0", "diamond.eqpeV_GW0")]:
                Path(dst).write_bytes((TEST_DATA / src).read_bytes())
            self.assertIn("G0W0 band structure", self.invoke("analyze-eqpev").output)
            self.assertIn("KS band structure", self.invoke("analyze-eqpev", "-g", "ks").output)
            self.assertIn("GW0 band structure", self.invoke("analyze-eqpev", "-g", "gw0").output)

    def test_degw_of_identical_energy_files(self):
        """the correction between a file and itself is zero"""
        penergy = str(TEST_DATA / "1.energy")
        with self.runner.isolated_filesystem():
            self.invoke("degw", "--diff", penergy, penergy, "-b", "1", "-o", "d.dat")
            rows = [l.split() for l in Path("d.dat").read_text().splitlines()
                    if l.strip() and not l.startswith("#")]
            self.assertTrue(rows)
            self.assertTrue(all(float(r[1]) == 0.0 for r in rows))

    def test_degw_rejects_different_kpoints(self):
        with self.runner.isolated_filesystem():
            result = self.runner.invoke(main, ["gap", "degw", "--diff", str(TEST_DATA / "1.energy"),
                                               str(TEST_DATA / "2.energy")])
            self.assertIsInstance(result.exception, ValueError)

    def test_degw_ap_requires_qtl(self):
        with self.runner.isolated_filesystem():
            result = self.runner.invoke(main, ["gap", "degw", "-e", str(TEST_DATA / "diamond_1.eqpeV_GW"),
                                               "--ap", "C:s"])
            self.assertIn("qtl must be parsed", str(result.exception))

    def test_vmat_plot(self):
        pvmat = str(TEST_DATA / "1_diamond_q1.vmat")
        with self.runner.isolated_filesystem():
            self.invoke("vmat", pvmat, "--plot", "--cz", "-s", "10")
            self.assertTrue(Path("vmat.png").exists())
            self.assertTrue(Path("first_nega_eigvec.png").exists())
            self.invoke("vmat", pvmat, "--plot", "--diff", pvmat, "-s", "-10")
            self.assertTrue(Path("diff_vmat.png").exists())

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

    def test_convert_requires_input(self):
        self.assertEqual(self.runner.invoke(main, ["cell", "convert"]).exit_code, 2)

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


class test_remaining_commands(ut.TestCase):

    LIBRPA_STDOUT = """
spin  1, k-point    1: (0.00000, 0.00000, 0.00000)
---------------------------------------------------------------
State   occ   e_mf   v_xc   v_exx   ReSigc   ImSigc   e_qp
---------------------------------------------------------------
    1   2.00000   -5.57966   -13.26760   -14.13742   1.94627   -0.04455   -4.50347
    2   0.00000   -2.60827   -15.34527   -10.17580   -3.36010   -0.06585   -0.79917

"""
    SBATCH_TEMPLATE = "#!/bin/bash\n#SBATCH -N 1\nsrun hello\n"

    def setUp(self):
        self.runner = CliRunner()

    def invoke(self, *args):
        result = self.runner.invoke(main, list(args))
        self.assertIsNone(result.exception, msg=result.output)
        return result

    def test_librpa_gap(self):
        with self.runner.isolated_filesystem():
            Path("librpa.out").write_text(self.LIBRPA_STDOUT)
            self.assertIn("gap", self.invoke("librpa", "gap", "librpa.out").output.lower())

    def test_eos_names(self):
        self.assertEqual(_AVAILABLE_EOS, available_eos)

    def test_fiteos(self):
        data = "\n".join("{} {}".format(v, -5.0 + 0.02 * (v - 20.0)**2 + 0.0004 * (v - 20.0)**3)
                         for v in (17.0, 18.0, 19.0, 19.5, 20.0, 20.5, 21.0, 22.0, 23.0))
        with self.runner.isolated_filesystem():
            Path("eos.dat").write_text(data)
            self.assertIn("V0 =", self.invoke("fiteos", "eos.dat").output)
            self.assertTrue(Path("eos.dat_fitted").exists())

    def test_quickgrace_legend_and_optional_symbol(self):
        with self.runner.isolated_filesystem():
            Path("xy.dat").write_text("0 1 2\n1 3 5\n2 5 9\n")
            self.invoke("quickgrace", "xy.dat", "--xy", "0:1", "0:2", "--l-add-fn", "-s")
            agr = Path("xy_quickgp.agr").read_text()
            self.assertIn("xy.dat:0:1", agr)
            self.assertIn("xy.dat:0:2", agr)

    def test_fiteos_e0_not_in_data(self):
        data = "\n".join("{} {}".format(v, -5.0 + 0.02 * (v - 20.0)**2 + 0.0004 * (v - 20.0)**3)
                         for v in (17.0, 18.0, 19.0, 19.5, 20.0, 20.5, 21.0, 22.0, 23.0))
        with self.runner.isolated_filesystem():
            Path("eos.dat").write_text(data)
            self.assertIn("V0 =", self.invoke("fiteos", "eos.dat", "-e", "-4.9").output)

    def test_quickgrace_yscale(self):
        with self.runner.isolated_filesystem():
            Path("xy.dat").write_text("1 1\n2 3\n3 9\n")
            self.invoke("quickgrace", "xy.dat", "--yscale", "log", "-o", "y.agr")
            agr = Path("y.agr").read_text()
            self.assertIn("yaxes scale Logarithmic", agr)
            self.assertNotIn("xaxes scale Logarithmic", agr)

    def test_quickgrace_exclusive_options(self):
        args = ["quickgrace", "a.dat", "-x", "1", "--xy", "0:1"]
        self.assertEqual(self.runner.invoke(main, args).exit_code, 2)

    def test_job_submit_with_dependency(self):
        fake = '#!/bin/sh\necho "$@" > sbatch.args\necho Submitted batch job 41\n'
        with self.runner.isolated_filesystem():
            cwd = Path(".").resolve()
            Path("sacct").write_text("#!/bin/sh\nexit 0\n")
            Path("fake_sbatch").write_text(fake)
            Path("t.sh").write_text(self.SBATCH_TEMPLATE)
            for name in ("sacct", "fake_sbatch"):
                Path(name).chmod(0o755)
            Path("c1").mkdir()
            Path("c2").mkdir()
            with patch.dict(os.environ, {"PATH": f"{cwd}:{os.environ['PATH']}"}):
                output = self.invoke("job", "submit", "t.sh", "--cmd", "fake_sbatch",
                                     "--dep", "ok", "--dep-jobid", "7").output
            self.assertIn("Newly submitted tasks: 2", output)
            args = sorted(Path(d, "sbatch.args").read_text().strip() for d in ("c1", "c2"))
            self.assertEqual(args, ["--dependency=afterok:41 t.sh", "--dependency=afterok:7 t.sh"])
            self.assertTrue(Path("c1/.submitted").exists())

    def test_job_submit_dry(self):
        with self.runner.isolated_filesystem():
            Path("t.sh").write_text(self.SBATCH_TEMPLATE)
            Path("c1").mkdir()
            self.assertIn("exiting as dry-run", self.invoke("job", "submit", "t.sh", "--dry").output)
            self.assertTrue(Path("c1/t.sh").exists())
            self.assertFalse(Path("c1/.submitted").exists())


if __name__ == "__main__":
    ut.main()
