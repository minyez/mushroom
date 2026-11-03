"""Unified readers using real program fixtures."""
import tempfile
import shutil
import unittest as ut
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
DATA = Path(__file__).parent / "data"
AIMS = ROOT / "mushroom/aims/test/data"


class test_spin_readers(ut.TestCase):

    def test_w2k_spin(self):
        from mushroom.w2k import read_energy
        # Reusing an actual channel represents the nonmagnetic spin-degenerate case.
        bs, _, _, _ = read_energy(DATA / "1.energy", DATA / "1.energy")
        self.assertEqual(bs.nspins, 2)
        np.testing.assert_equal(bs.eigen[0], bs.eigen[1])

    def test_aims_spin(self):
        from mushroom.aims.band import read_band_mulliken_output, read_band_output
        bs, _ = read_band_mulliken_output(AIMS / "GaAs_spin_bandmlk1001.out",
                                         bfiles_spin=[AIMS / "GaAs_spin_bandmlk2001.out"])
        self.assertEqual(bs.nspins, 2)
        # First state at first k point, from the real files, independently inspected.
        self.assertEqual(bs.eigen[0, 0, 0], -11876.29005)
        self.assertEqual(bs.eigen[1, 0, 0], -11876.29005)
        bs, _ = read_band_output(AIMS / "Si_GW_band1001.out",
                                bfiles_spin=[AIMS / "Si_GW_band1001.out"])
        self.assertEqual(bs.nspins, 2)
        np.testing.assert_equal(bs.eigen[0], bs.eigen[1])

    def test_vasp_spin(self):
        from mushroom.vasp import read_eigen
        bs, _, _ = read_eigen(DATA / "EIGENVAL_2")
        self.assertEqual(bs.nspins, 2)
        self.assertEqual(bs.eigen[0, 0, 0], -23.405535)
        self.assertEqual(bs.eigen[1, 0, 0], -23.476234)


class test_band_io(ut.TestCase):

    def test_vasp(self):
        from mushroom.io import read_band, read_dos
        from mushroom.vasp import read_eigen, read_doscar
        data = read_band(ROOT / "examples/vasp")
        bs, _, _ = read_eigen(ROOT / "examples/vasp/EIGENVAL")
        np.testing.assert_equal(data.bs.eigen, bs.eigen)
        self.assertIsNotNone(data.recp_latt)
        dos = read_dos(ROOT / "examples/vasp")
        np.testing.assert_equal(dos.tdos, read_doscar(ROOT / "examples/vasp/DOSCAR").tdos)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "a.npz"
            data.save(path)
            np.testing.assert_equal(read_band(path).bs.eigen, bs.eigen)
            dos.save(path)
            np.testing.assert_equal(read_dos(path).tdos, dos.tdos)

    def test_aims_w2k(self):
        from mushroom.io import read_band, read_dos
        from mushroom.aims.band import read_band_output
        from mushroom.w2k import read_energy
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            shutil.copy(AIMS / "Si_GW_band1001.out", root / "GW_band1001.out")
            (root / "control.in").touch()
            result = read_band(root, kind="gw")
            bs, _ = read_band_output(AIMS / "Si_GW_band1001.out")
            np.testing.assert_equal(result.bs.eigen, bs.eigen)
            dos = read_dos(root, code="aims", kind="gw")
            self.assertEqual(dos.nspins, 1)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for suffix in ("struct", "energy"):
                shutil.copy(DATA / ("1." + suffix), root / ("case." + suffix))
            (root / "case.in0").touch()
            result = read_band(root)
            bs, _, _, _ = read_energy(DATA / "1.energy")
            np.testing.assert_equal(result.bs.eigen, bs.eigen)
            self.assertIsNotNone(result.recp_latt)

    def test_dispatch_errors(self):
        from mushroom.io import read_band
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with self.assertRaisesRegex(ValueError, "code="):
                read_band(root)
            (root / "INCAR").touch()
            (root / "control.in").touch()
            with self.assertRaisesRegex(ValueError, "aims.*vasp|vasp.*aims"):
                read_band(root)
            for code in ("qe", "abacus", "abi", "yambo", "w90"):
                with self.assertRaisesRegex(NotImplementedError, "vasp"):
                    read_band(root, code=code)
        with self.assertRaisesRegex(ValueError, "code="):
            read_band("unknown.output")
        with self.assertRaises(ValueError):
            read_band(ROOT / "examples/vasp", kind="gw")

    def test_explicit_projection_paths(self):
        from mushroom.io import read_band
        from mushroom.vasp import read_procar
        data = read_band(DATA / "PROCAR_1")
        bs, _ = read_procar(DATA / "PROCAR_1")
        np.testing.assert_equal(data.bs.eigen, bs.eigen)
        self.assertTrue(data.bs.has_proj())
        data = read_band(AIMS / "Si_bandmlk1001.out")
        self.assertTrue(data.bs.has_proj())
        data = read_band(DATA / "1.energy")
        self.assertEqual(data.bs.nkpts, 4)

    def test_path_metadata_and_projection_dispatch(self):
        from mushroom.io import read_band, read_dos
        from mushroom.vasp import read_kpath_symbols
        self.assertIsNone(read_kpath_symbols(DATA/"KPOINTS_1"))
        self.assertEqual(read_kpath_symbols(DATA/"KPOINTS_3"), ["gamma", "X", "W", "gamma"])
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            shutil.copy(DATA/"PROCAR_1", root/"PROCAR")
            shutil.copy(DATA/"KPOINTS_3", root/"KPOINTS")
            result = read_band(root/"EIGENVAL", code="vasp", projections=True, unit="ry", efermi=0.)
            self.assertEqual(result.bs.unit, "ry")
            self.assertTrue(result.bs.has_proj())
            self.assertEqual(result.ksymbols, ["gamma", "X", "W", "gamma"])
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            shutil.copy(AIMS/"GaAs_spin_bandmlk1001.out", root/"bandmlk1001.out")
            shutil.copy(AIMS/"GaAs_spin_bandmlk2001.out", root/"bandmlk2001.out")
            result = read_band(root/"bandmlk1001.out", code="aims", efermi=1.)
            self.assertEqual(result.bs.nspins, 2)
            self.assertAlmostEqual(result.bs.eigen[0, 0, 0], -11875.29005)
            result = read_band(root, code="aims", projections=True)
            self.assertEqual(result.bs.nspins, 2)
            with self.assertRaises(FileNotFoundError):
                read_band(root, code="aims", kind="gw")
            with self.assertRaises(ValueError):
                read_band(root, code="aims", kind="qp")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for suffix in ("struct", "energy"):
                shutil.copy(DATA/("1."+suffix), root/("case."+suffix))
            result = read_band(root, code="w2k", unit="ev")
            self.assertEqual(result.bs.unit, "ev")
            with self.assertRaises(ValueError):
                read_band(root, code="w2k", kind="qp")
            with self.assertRaises(FileNotFoundError):
                read_dos(root, code="w2k")
