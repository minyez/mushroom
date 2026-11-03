"""CLI integration tests for portable data analysis and plotting."""
import tempfile
import unittest as ut
from unittest.mock import patch
from pathlib import Path

from click.testing import CliRunner
import numpy as np

try:
    import matplotlib
    matplotlib.use("Agg")
except ImportError:
    matplotlib = None

from mushroom.cli import main
from mushroom.core.bs import BandStructure, BandPathData
from mushroom.core.dos import DensityOfStates


PLT_INSTALLED = matplotlib is not None
ROOT = Path(__file__).resolve().parents[2]


class test_band_cli(ut.TestCase):

    def setUp(self):
        self.runner = CliRunner()
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "a.npz"
        bs = BandStructure([[[-2, -1, 2, 4], [-3, 0, 3, 5], [-2, -1, 2, 4]]], efermi=1.)
        BandPathData(bs, np.array([[0, 0, 0], [.25, 0, 0], [.5, 0, 0]]), np.eye(3)).save(self.path)
        self.dospath = Path(self.tmp.name) / "d.npz"
        DensityOfStates([-1, 0, 1], [[2, 3, 2]]).save(self.dospath)

    def run_ok(self, args):
        result = self.runner.invoke(main, list(map(str, args)))
        self.assertEqual(result.exit_code, 0, str(result.exception) + result.output)
        return result

    def test_data_grace(self):
        target = Path(self.tmp.name)
        self.run_ok(["band", self.path, "--save", target/"copy.npz", "--data"])
        for inp, out in [(self.path, "a.agr"), (target/"copy.npz", "b.agr")]:
            self.run_ok(["band", inp, "--engine", "grace", "-o", target/out])
        # Separate CLI processes initialize different invisible Grace timestamps.
        from mushroom.visual.graceplot import _TimesStamp
        for stamp, inp, out in [("first", self.path, "a.agr"), ("later", target/"copy.npz", "b.agr")]:
            with patch.dict(_TimesStamp._attrs, {"def": (str, stamp, "\"{:s}\"")}):
                self.run_ok(["band", inp, "--engine", "grace", "-o", target/out])
        self.assertEqual((target/"a.agr").read_text(), (target/"b.agr").read_text())
        new = self.run_ok(["band", ROOT/"examples/vasp", "--data"])
        old = self.run_ok(["vasp", "band", "-v", ROOT/"examples/vasp/EIGENVAL",
                           "--pos", ROOT/"examples/vasp/POSCAR", "--data"])
        self.assertEqual(new.output, old.output)
        self.run_ok(["band", self.path, self.path, "--labels", "a", "b", "--engine", "grace", "-o", target/"c.agr"])
        self.run_ok(["dos", self.dospath, self.dospath, "--labels", "a", "b", "--engine", "grace", "-o", target/"d.agr"])
        with self.runner.isolated_filesystem():
            self.run_ok(["dos", self.dospath, "--data", "--save", "saved.npz"])
            self.assertTrue(Path("tdos.dat").is_file())

    def test_usage(self):
        for args in [[str(self.path), str(self.path), "--apb", "0:s"],
                     [str(self.path), "--ref", "vbm", "--align", "ef"],
                     [str(self.path), "--align", "ef"],
                     [str(self.path), "--labels", "a", "b"]]:
            result = self.runner.invoke(main, ["band"] + args)
            self.assertEqual(result.exit_code, 2, result.output)
        with patch.dict("sys.modules", {"matplotlib.pyplot": None}):
            result = self.runner.invoke(main, ["band", str(self.path)])
        self.assertIn("mushroom[plot]", result.output)
        self.assertIn("--engine grace", result.output)

    @ut.skipUnless(PLT_INSTALLED, "requires matplotlib")
    def test_matplotlib(self):
        with self.runner.isolated_filesystem():
            self.run_ok(["band", self.path])
            self.assertTrue(Path("plotband.pdf").is_file())
            self.run_ok(["band", self.path, "--dos", self.dospath, "-o", "both.png", "--savefig", "eps"])
            self.assertTrue(Path("both.png").is_file())
            self.run_ok(["dos", self.dospath])
            self.assertTrue(Path("plotdos.pdf").is_file())
            self.run_ok(["dos", self.dospath, self.dospath, "-e", "m2~3", "-o", "dos.png"])

    def test_effective_mass(self):
        from mushroom.core.test.test_effective_mass import test_effective_mass
        make_data = test_effective_mass().make_data
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/"mass.npz"
            make_data(np.linspace(0, .5, 21)).save(path)
            result = CliRunner().invoke(main, ["emass", str(path)])
            self.assertEqual(result.exit_code, 0, str(result.exception))
            self.assertIn("cbm k=0", result.output)
            result = CliRunner().invoke(main, ["emass", str(path), "--band", "1", "--k", "0", "-n", "5"])
            self.assertEqual(result.exit_code, 0, str(result.exception))

    @ut.skipUnless(PLT_INSTALLED, "requires matplotlib")
    def test_projected_plots_and_output(self):
        from mushroom.visual.graceplot import Plot
        from mushroom.cli.band import _finish
        bs = BandStructure([[[-2, 2], [-1, 3], [-2, 2]]], efermi=0.,
                           pwav=np.ones((1, 3, 2, 1, 1)), atms=["Si"], prjs=["s"])
        BandPathData(bs, np.array([[0, 0, 0], [.25, 0, 0], [.5, 0, 0]])).save(self.path)
        DensityOfStates([-1, 0, 1], [[2, 3, 2]], pdos=np.ones((1, 3, 1, 1)),
                        atms=["Si"], prjs=["s"]).save(self.dospath)
        with self.runner.isolated_filesystem():
            self.run_ok(["band", self.path, "--apb", "Si:s:0", "--spin", "up", "--area", "-o", "fat.png"])
            self.run_ok(["dos", self.dospath, "--aps", "Si:s", "--data"])
            self.assertIn("#atom-projector:Si:s", Path("pdos.dat").read_text())
            result = self.runner.invoke(main, ["dos", str(self.dospath), str(self.dospath), "--save", "bad.npz"])
            self.assertEqual(result.exit_code, 2)
            with patch.object(Plot, "savefig") as savefig:
                self.run_ok(["band", self.path, "--engine", "grace", "--savefig", "png"])
                savefig.assert_called_once_with("plotband.png")
            import matplotlib.pyplot as plt
            fig, _ = plt.subplots()
            with patch("matplotlib.get_backend", return_value="TkAgg"), patch.object(plt, "show") as show:
                _finish(fig, "plt", None, "unused")
                show.assert_called_once()
            self.run_ok(["qp-corr", ROOT/"mushroom/test/data/diamond_1.eqpeV_GW", "--fit", "-o", "qp.png"])
            Path("empty").mkdir()
            self.run_ok(["collect", "empty", "--plot", "nkpts:energy", "-o", "collect.png"])
