"""Regression tests for the second data visualization review."""
from pathlib import Path
import shutil
import tempfile
import unittest as ut
from unittest.mock import patch

import numpy as np

try:
    import matplotlib
    matplotlib.use("Agg")
except ImportError:
    matplotlib = None

from mushroom.io import read_band, read_dos

PLT_INSTALLED = matplotlib is not None
ROOT = Path(__file__).resolve().parents[2]


class test_reader_regressions(ut.TestCase):

    def test_fermi_resets_occupations(self):
        path = ROOT / "examples/vasp/EIGENVAL"
        original = read_band(path).bs
        shifted = read_band(path, efermi=20.).bs
        np.testing.assert_array_equal(shifted.occ, shifted.eigen <= 20.)
        self.assertGreater(np.count_nonzero(shifted.occ), np.count_nonzero(original.occ))
        self.assertGreater(shifted.vbm, original.vbm)
        np.testing.assert_array_equal(shifted.eigen, original.eigen)

    def test_w2k_dos_selection(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            shutil.copy(ROOT / "mushroom/test/data/1.struct", root / "case.struct")
            for name in ("case.dos1", "case.dos2", "case.dos10ev", "case.dos2ev", "case.dos1ev",
                         "case.dos1evup", "case.dos1evdn", "other.dos1ev", "case.dos1ev.bak"):
                (root / name).touch()
            with patch("mushroom.w2k.read_dos") as reader:
                read_dos(root, code="w2k", casename="case")
            self.assertEqual(reader.call_args.args, tuple(root / name for name in
                             ("case.dos1ev", "case.dos2ev", "case.dos10ev")))


@ut.skipUnless(PLT_INSTALLED, "requires matplotlib")
class test_color_regressions(ut.TestCase):

    def test_reference_line_colors(self):
        import matplotlib.pyplot as plt
        from mushroom.visual.axes import wrap_axes
        fig, ax = plt.subplots()
        self.addCleanup(plt.close, fig)
        adapter = wrap_axes(ax)
        for method in (adapter.axhline, adapter.axvline):
            self.assertEqual(method(0, color="green4").get_color(), "#008b00")
            self.assertEqual(method(1, color="grey").get_color(), "#dcdcdc")


class test_public_interfaces(ut.TestCase):

    def test_cli_help(self):
        import click
        from click.testing import CliRunner
        from mushroom.cli import main
        for name in ("band", "dos", "qp-corr", "emass", "collect"):
            command = main.commands[name]
            result = CliRunner().invoke(main, [name, "-h"])
            self.assertEqual(result.exit_code, 0, result.output)
            for option in command.params:
                if isinstance(option, click.Option):
                    self.assertTrue(option.help, (name, option.name))
            for option in command.params:
                if isinstance(option, click.Option) and option.multiple:
                    self.assertTrue(option.metavar.endswith("..."), (name, option.name))
        spin = next(p for p in main.commands["vasp"].commands["band"].params if p.name == "spin")
        self.assertTrue(spin.help)

    def test_timestamp(self):
        from mushroom.visual.graceplot import Plot
        fig, _ = Plot.subplots()
        fig.set_timestamp("fixed time")
        self.assertIn("@timestamp def \"fixed time\"", str(fig))
        fig.set_timestamp("")
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "a.agr"
            fig.write(file=path)
            self.assertIn("@timestamp def \"\"", path.read_text())

    def test_detect_code(self):
        import mushroom.io as io
        self.assertIn("detect_code", io.__all__)
        for filename, code in (("EIGENVAL", "vasp"), ("band1001.out", "aims"),
                               ("case.dos1ev", "w2k"), ("librpa.out", "librpa"),
                               ("case.eqpeV", "gap")):
            self.assertEqual(io.detect_code(filename), code)
        self.assertEqual(io.detect_code("unknown", "VASP"), "vasp")
        with self.assertRaisesRegex(ValueError, "specify code"):
            io.detect_code("unknown")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "INCAR").touch()
            self.assertEqual(io.detect_code(root), "vasp")
            (root / "control.in").touch()
            with self.assertRaisesRegex(ValueError, "Ambiguous"):
                io.detect_code(root)

    def test_w2k_selection_errors(self):
        from mushroom.io import _w2k_dos_files
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "case.dos1").touch()
            (root / "other.dos1ev").touch()
            (root / "case.dos2ev").mkdir()
            with self.assertRaises(FileNotFoundError):
                _w2k_dos_files(root, "case")
            (root / "case.dos1evup").touch()
            (root / "case.dos1evdn").touch()
            with self.assertRaisesRegex(NotImplementedError, "explicit file paths"):
                _w2k_dos_files(root, "case")
            (root / "case.dos1ev").touch()
            self.assertEqual(_w2k_dos_files(root, "case"), [root / "case.dos1ev"])

    def test_kpath_properties_and_mass_index(self):
        from mushroom.core.bs import effective_mass
        from mushroom.core.test.test_effective_mass import test_effective_mass
        data = test_effective_mass().make_data(np.linspace(0, .5, 21))
        data.ksymbols = ["Gamma", "X"]
        kp = data.kpath()
        self.assertEqual(kp.ksymbols, ("Gamma", "X"))
        self.assertEqual(kp.nkpts, 21)
        self.assertEqual(kp.segments, ((0, 20),))
        self.assertTrue(kp.is_cartesian)
        np.testing.assert_allclose(kp.kpts, data.kpts @ data.recp_latt)
        kp.kpts[:] = 99  # A returned array must not mutate the path.
        np.testing.assert_allclose(kp.kpts, data.kpts @ data.recp_latt)
        data.ksymbols[0] = "changed"
        self.assertEqual(kp.ksymbols[0], "Gamma")
        for name in ("ksymbols", "nkpts", "segments", "kpts", "is_cartesian"):
            with self.assertRaises(AttributeError):
                setattr(kp, name, None)
        for band in ("vbm", "cbm"):
            result = effective_mass(data.bs, kp, band, None)
            self.assertEqual(result["ik"], 0)
            self.assertEqual(result["right_label"], "Gamma→X")
        self.assertEqual(effective_mass(data.bs, kp, "cbm", 10)["ik"], 10)

    def test_qp_has_no_dynamic_band_origin(self):
        from mushroom.io import read_qp_pair
        ks, qp = read_qp_pair(ROOT / "mushroom/test/data/diamond_1.eqpeV_GW")
        self.assertNotIn("band_start", vars(ks))
        self.assertNotIn("band_start", vars(qp))

    def test_vasp_collect_reads_once(self):
        from mushroom.collect import collect_dir, _vasp
        from mushroom.test.test_vasp import test_outcar
        from mushroom.vasp import read_eigen
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "OUTCAR").write_text(test_outcar.text)
            shutil.copy(ROOT / "examples/vasp/EIGENVAL", root / "EIGENVAL")
            with patch("mushroom.vasp.read_eigen", wraps=read_eigen) as reader:
                _, fields = _vasp(root)
                reader.assert_not_called()
                for key in ("gap", "gap_direct", "efermi", "nkpts"):
                    self.assertIsNotNone(fields[key]())
                reader.assert_called_once()
            with patch("mushroom.vasp.read_eigen", side_effect=ValueError("damaged eigenvalues")) as reader:
                row = collect_dir(root, code="vasp")
                reader.assert_called_once()
            self.assertEqual(row["energy"], -10.4)
            for key in ("gap", "gap_direct", "efermi", "nkpts"):
                self.assertIsNone(row[key])
                self.assertIn(key + ": damaged eigenvalues", row["error"])
            # A gap-specific failure must not prevent other fields from using the bands.
            with patch("mushroom.core.bs.BandStructure.fund_gap", side_effect=ValueError("gap unavailable")):
                row = collect_dir(root, code="vasp")
            self.assertIsNone(row["gap"])
            self.assertIsNotNone(row["gap_direct"])
            self.assertEqual(row["nkpts"], 4)


@ut.skipUnless(PLT_INSTALLED, "requires matplotlib")
class test_plot_defaults(ut.TestCase):

    def test_backend_registry_and_fallback(self):
        import builtins
        import warnings
        from mushroom.visual.pyplot import is_interactive_backend
        with warnings.catch_warnings():
            warnings.simplefilter("error", DeprecationWarning)
            for name, expected in (("Agg", False), ("TkAgg", True), ("PDF", False)):
                with patch("matplotlib.get_backend", return_value=name):
                    self.assertEqual(is_interactive_backend(), expected)
        # Emulate the old public API without accessing the deprecated modern attribute.
        from types import SimpleNamespace
        original_import = builtins.__import__

        def legacy_import(name, globals=None, locals=None, fromlist=(), level=0):
            if name == "matplotlib.backends" and "backend_registry" in fromlist:
                raise ImportError("old matplotlib")
            if name == "matplotlib.rcsetup":
                return SimpleNamespace(interactive_bk=["TkAgg"])
            return original_import(name, globals, locals, fromlist, level)

        with patch("builtins.__import__", side_effect=legacy_import):
            for name, expected in (("tKAgG", True), ("agg", False)):
                with patch("matplotlib.get_backend", return_value=name):
                    self.assertEqual(is_interactive_backend(), expected)

    def test_blank_ticks_and_source_labels(self):
        import matplotlib.pyplot as plt
        from mushroom.core.bs import BandStructure, BandPathData
        from mushroom.visual.bandplot import plot_band, plot_bands_compare
        from mushroom.visual.graceplot import Plot
        bs = BandStructure([[[-1, 1], [-2, 2], [-1, 1]]], efermi=0.)
        data = BandPathData(bs, np.array([[0, 0, 0], [.25, 0, 0], [.5, 0, 0]]),
                            code="vasp", source="calc/EIGENVAL;calc/POSCAR")
        fig, ax = plt.subplots()
        self.addCleanup(plt.close, fig)
        plot_band(ax, bs, data.kpath())
        self.assertEqual([t.get_text() for t in ax.get_xticklabels()], ["", ""])
        ax.clear()
        plot_bands_compare(ax, [data])
        self.assertEqual(ax.get_legend_handles_labels()[1], ["calc"])
        data.source = ""
        ax.clear()
        plot_bands_compare(ax, [data])
        self.assertEqual(ax.get_legend_handles_labels()[1], ["vasp"])
        grace, graph = Plot.subplots()
        plot_band(graph, bs, data.kpath())
        self.assertIn("ticklabel 0, \"\"", str(grace))

    def test_cli_symbols_and_dos_labels(self):
        from click.testing import CliRunner
        from mushroom.cli import main
        from mushroom.core.bs import BandStructure, BandPathData
        from mushroom.core.dos import DensityOfStates
        from mushroom.visual.bandplot import plot_band
        from mushroom.visual.dosplot import plot_dos
        runner = CliRunner()
        with runner.isolated_filesystem():
            bs = BandStructure([[[-1, 1], [-2, 2], [-1, 1]]], efermi=0.)
            BandPathData(bs, np.array([[0, 0, 0], [.25, 0, 0], [.5, 0, 0]])).save("band.npz")
            DensityOfStates([-1, 0, 1], [[1, 2, 1]]).save("dos.npz")
            for symbols in (["G X"], ["G", "X"]):
                with patch("mushroom.visual.bandplot.plot_band", wraps=plot_band) as plot:
                    result = runner.invoke(main, ["band", "band.npz", "--sym", *symbols, "-o", "band.pdf"])
                self.assertEqual(result.exit_code, 0, str(result.exception))
                self.assertEqual(plot.call_args.kwargs["ksymbols"], ["G", "X"])
            for args, expected in (([], ["Total"]), (["--labels", "my DOS"], ["my DOS"]),
                                   (["dos.npz"], ["dos.npz", "dos.npz"])):
                with patch("mushroom.visual.dosplot.plot_dos", wraps=plot_dos) as plot:
                    result = runner.invoke(main, ["dos", "dos.npz", *args, "-o", "dos.pdf"])
                self.assertEqual(result.exit_code, 0, str(result.exception))
                self.assertEqual([call.kwargs["label_total"] for call in plot.call_args_list], expected)
