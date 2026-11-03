"""Backend parity, spin plotting and legacy text exports."""
import tempfile
import unittest as ut
from unittest.mock import patch
from pathlib import Path

import numpy as np

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
except ImportError:
    plt = None

from mushroom.core.bs import BandStructure, BandPathData
from mushroom.core.dos import DensityOfStates
from mushroom.core.kpoints import KPathLinearizer
from mushroom.visual.axes import wrap_axes
from mushroom.visual.graceplot import Plot
from mushroom.visual.bandplot import (plot_band, plot_fatband, export_fatband_data,
                                      plot_band_dos, plot_bands_compare, bandplot)
from mushroom.visual.dosplot import plot_dos, export_tdos_data, export_pdos_data

PLT_INSTALLED = plt is not None
ROOT = Path(__file__).resolve().parents[3]


def bands(nspins=1):
    """Analytic tiny bands with a known zero VBM and gap two."""
    eigen = np.tile([[[-3, -1, 2, 4], [-2, 0, 3, 5], [-3, -1, 2, 4]]], (nspins, 1, 1))
    return BandStructure(eigen, efermi=1, pwav=np.ones((nspins, 3, 4, 1, 1)), atms=["Si"], prjs=["s"])


class test_exports(ut.TestCase):

    def test_legacy_bytes(self):
        from mushroom.vasp import read_procar, read_doscar
        bs, _ = read_procar(ROOT / "mushroom/test/data/PROCAR_1")
        dos = read_doscar(ROOT / "examples/vasp/DOSCAR")
        for name, lines in [("pwav", export_fatband_data(bs, ["0:s:0"])),
                            ("tdos", export_tdos_data(dos)), ("pdos", export_pdos_data(dos, ["0:s"]))]:
            expected = (Path(__file__).parent / "data" / (name + ".dat")).read_text()
            self.assertEqual("\n".join(lines) + "\n", expected)


class test_grace(ut.TestCase):

    def test_lines_and_styles(self):
        kp = KPathLinearizer([[0, 0, 0], [.25, 0, 0], [.5, 0, 0]])
        for nspin in (1, 2):
            fig, ax = Plot.subplots()
            self.assertIs(plot_band(ax, bands(nspin), kp, zero_line=False, set_xaxis=False), ax)
            self.assertEqual(ax.ndata, 4 * nspin)
            with tempfile.TemporaryDirectory() as tmp:
                p = Path(tmp) / "a.agr"
                fig.write(file=p)
                text = p.read_text()
                if nspin == 2:
                    self.assertIn("s4 line linestyle 3", text)
        with self.assertRaises(ValueError):
            plot_band(ax, bands(), kp, spin=1)
        with self.assertRaises(ValueError):
            plot_band(ax, bands(), kp, ksymbols=["X"])
        with self.assertRaises(TypeError):
            wrap_axes(None)
        adapter = wrap_axes(ax)
        self.assertIs(wrap_axes(adapter), adapter)
        with self.assertRaises(ValueError):
            adapter.line([0], [0], color="unknown")
        adapter.line([0, 1], [0, 1], ls="dashdot", marker="s", ms=6)
        adapter.set_xlabel("x")
        adapter.set_ylim(-1, 1)
        adapter.legend()
        with patch("mushroom.visual.axes._logger.warning") as warn:
            adapter.fill_between([0], [1], "red")
            warn.assert_called_once()

    def test_plots(self):
        bs = bands(2)
        kp = KPathLinearizer([[0, 0, 0], [.25, 0, 0], [.5, 0, 0]])
        dos = DensityOfStates([-1, 0, 1], [[2, 3, 2], [1, 2, 1]],
                              pdos=np.ones((2, 3, 1, 1)), atms=["Si"], prjs=["s"])
        _, ax = Plot.subplots()
        plot_fatband(ax, bs, kp, ["Si:s:0"], prop_area=True)
        plot_fatband(ax, bs, kp, ["Si:s:0"], prop_area=False)
        plot_band(ax, bs, kp, bands=(0, -1), ksymbols=["Gamma", "K|U"], resolve=[((0, 1), None)])
        plot_bands_compare(ax, [(bs, kp, "a"), (bs, kp, "b")])
        plot_dos(ax, dos, aps=["Si:s"], fill=True)
        plot_band_dos(bs, kp, dos, engine="grace", aps=["Si:s"])
        with self.assertRaises(ValueError):
            plot_dos(ax, dos, spin=2)
        with self.assertRaises(ValueError):
            plot_dos(ax, dos, ref="bad")
        with self.assertRaises(ValueError):
            plot_dos(ax, dos, orientation="bad")


@ut.skipUnless(PLT_INSTALLED, "requires matplotlib")
class test_matplotlib(ut.TestCase):

    def tearDown(self):
        plt.close("all")

    def test_spins(self):
        kp = KPathLinearizer([[0, 0, 0], [.25, 0, 0], [.5, 0, 0]])
        for nspin in (1, 2):
            _, ax = plt.subplots()
            plot_band(ax, bands(nspin), kp, zero_line=False, set_xaxis=False)
            self.assertEqual(len(ax.lines), nspin * 4)
            for i, line in enumerate(ax.lines):
                self.assertEqual(line.get_color(), "black" if nspin == 1 else ("blue" if i < 4 else "red"))
                self.assertEqual(line.get_linestyle(), "-" if i < 4 else "--")
        _, ax = plt.subplots()
        plot_band(ax, bands(2), kp, spin=1, bands=[0, 2], label="data", ksymbols=["Gamma", "X"])
        self.assertEqual(ax.lines[0].get_label(), "data (dn)")
        self.assertEqual(ax.get_xticklabels()[0].get_text(), "$\\Gamma$")
        plot_fatband(ax, bands(), kp, ["Si:s:0"], scale=2)
        np.testing.assert_equal(ax.collections[0].get_sizes(), [144] * 3)
        wrap_axes(ax).legend()
        wrap_axes(ax).set_xlabel("k")
        plot_bands_compare(ax, [BandPathData(bands(), kp._kpts),
                               (bands(), KPathLinearizer(kp._kpts * 2), "longer")], ls=["solid"])

    def test_dos_combined(self):
        dos = DensityOfStates([-1, 0, 1], [[2, 3, 2], [1, 2, 1]], efermi=.5,
                              pdos=np.ones((2, 3, 1, 1)), atms=["Si"], prjs=["s"])
        _, ax = plt.subplots()
        plot_dos(ax, dos, aps=["Si:s"], fill=True)
        np.testing.assert_equal(ax.lines[1].get_ydata(), [-1, -2, -1])
        plot_dos(ax, dos, ref=None, spin=0, orientation="vertical", fill=True, show_total=False, aps=["Si:s"])
        kp = KPathLinearizer([[0, 0, 0], [.25, 0, 0], [.5, 0, 0]])
        fig, (ab, ad) = plot_band_dos(bands(), kp, dos, dos_ref="efermi")
        self.assertEqual(ab.get_ylim(), ad.get_ylim())
        with tempfile.TemporaryDirectory() as tmp:
            fig.savefig(Path(tmp) / "plot.png")
        with self.assertWarns(DeprecationWarning):
            bandplot(bands(), kp, nbands_max=2)

    def test_units_spin_and_qp(self):
        from copy import deepcopy
        from mushroom.visual.bandplot import plot_qp_correction
        from mushroom.core.bs import fit_qp_correction
        kp = KPathLinearizer([[0, 0, 0], [.25, 0, 0], [.5, 0, 0]])
        bs = bands(2)
        other = deepcopy(bs)
        other.unit = "ry"
        _, ax = plt.subplots()
        plot_bands_compare(ax, [(bs, kp, "eV"), (other, kp, "Ry")], spin=1)
        self.assertEqual(other.unit, "ry")
        # Second group's first band shares the first group's energy scale.
        # First group includes zero and two grid guides after its four bands.
        np.testing.assert_allclose(ax.lines[0].get_ydata(), ax.lines[7].get_ydata())
        dos = DensityOfStates([-1, 0, 1], [[2, 3, 2], [1, 2, 1]])
        _, (ab, ad) = plot_band_dos(bs, kp, dos, spin=1)
        self.assertEqual(len(ad.lines), 1)
        self.assertTrue(np.all(ad.lines[0].get_xdata() <= 0))
        self.assertEqual(ad.get_ylabel(), "")
        e = np.array([-2., -1., 1., 2.])
        de = .1 * e + 1
        plot_qp_correction(ax, e, de, e < 0, fit=fit_qp_correction(e, de, e < 0))
        plot_qp_correction(ax, e, de, np.ones(4, dtype=bool))

    def test_default_palette_fill(self):
        dos = DensityOfStates([-1, 0, 1], [[2, 3, 2]],
                              pdos=np.ones((1, 3, 1, 1)), atms=["Si"], prjs=["s"])
        for orientation in ("horizontal", "vertical"):
            _, ax = plt.subplots()
            with patch("mushroom.visual.dosplot.DEFAULT_COLORS", ["red", "blue", "orange", "green4"]):
                plot_dos(ax, dos, aps=["Si:s"] * 4, show_total=False, fill=True, orientation=orientation)
            np.testing.assert_allclose(ax.collections[3].get_facecolor()[0, :3], [0, 139/255, 0])
