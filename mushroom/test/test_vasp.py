#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test vasp related utitlies"""
import unittest as ut
import pathlib
import json
import sys
import tempfile
import warnings
import numpy as np

from mushroom import vasp
from mushroom.core.cell import Cell


# check if BeautifulSoup installation. skip some tests if not installed
try:
    from bs4 import BeautifulSoup
    BeautifulSoup_INSTALLED = True
    del BeautifulSoup
except ImportError:
    BeautifulSoup_INSTALLED = False


class test_read_doscar(ut.TestCase):
    """test reading in DOSCAR to get a DensityOfStates object"""

    def test_read_testdata(self):
        """read test DOSCARs in data directory"""
        dir_doscar = pathlib.Path(__file__).parent / "data"
        index_json = dir_doscar / "doscar.json"
        with index_json.open('r') as fp:
            verifies = json.load(fp)
        for f, verify in verifies.items():
            print("Testing {}".format(f))
            fpath = dir_doscar / f
            dos = vasp.read_doscar(str(fpath))
            for k, v in verify.items():
                self.assertEqual(dos.__getattribute__(k), v)


class test_read_procar(ut.TestCase):
    """test reading in PROCAR to get a BandStructure object"""

    def test_read_testdata(self):
        """read test PROCARs in data directory"""
        dir_procar = pathlib.Path(__file__).parent / "data"
        index_json = dir_procar / "procar.json"
        with index_json.open('r') as fp:
            verifies = json.load(fp)
        for f, verify in verifies.items():
            print("Testing {}".format(f))
            fpath = dir_procar / f
            bs, _ = vasp.read_procar(str(fpath))
            for k, v in verify.items():
                self.assertEqual(bs.__getattribute__(k), v)


class test_read_xml(ut.TestCase):
    """test reading vasprunxml"""

    def test_read_kpts(self):
        """kpoints"""
        if not BeautifulSoup_INSTALLED:
            return
        dir_xml = pathlib.Path(__file__).parent / "data"
        index_json = dir_xml / "vasprunxml.json"
        with index_json.open('r') as fp:
            verifies = json.load(fp)
        for f, verify in verifies.items():
            print("Testing {}".format(f))
            fpath = dir_xml / f
            d = vasp.read_xml(*verify.keys(), path=str(fpath))
            for k, v in verify.items():
                self.assertTrue(np.allclose(d[k], v))


class test_eigenval(ut.TestCase):
    """test reading eigenval file"""

    def test_read_eigenval(self):
        """eigenval"""
        dir_eigen = pathlib.Path(__file__).parent / "data"
        index_json = dir_eigen / "eigenval.json"
        with index_json.open('r') as fp:
            verifies = json.load(fp)
        for f, verify in verifies.items():
            print("Testing {}".format(f))
            fpath = dir_eigen / f
            bs, natms, kpoints = vasp.read_eigen(path=str(fpath))
            self.assertEqual(natms, verify.pop("natms"))
            for k, v in verify.items():
                bsv = bs.__getattribute__(k)
                print(">> {} ?= {}".format(k, v))
                self.assertTrue(np.allclose(bsv, v))


class test_poscar(ut.TestCase):
    """test poscar reader. Actually tested in Cell"""


class test_wavecar(ut.TestCase):
    """test wavecar object"""

    def test_read_wavecar(self):
        """reading the predefined cases"""
        dir_wavecar = pathlib.Path(__file__).parent / "data"
        index_json = dir_wavecar / "wavecar.json"
        with index_json.open('r') as fp:
            verifies = json.load(fp)
        for f, verify in verifies.items():
            print("Testing {}".format(f))
            fpath = dir_wavecar / f
            wc = vasp.WaveCar(fpath)
            wc.get_ipw(0)
            wc.get_raw_coeff(0, 0, 0)
            for k, v in verify.items():
                wv = wc.__getattribute__(k)
                print(">> {} ?= {}".format(k, v))
                if isinstance(v, (list, tuple)):
                    self.assertTrue(np.allclose(v, wv))
                if isinstance(v, (int, float)):
                    self.assertEqual(v, wv)
            wc.close()


class test_kpoints(ut.TestCase):

    def test_read_kpoints(self):
        datadir = pathlib.Path(__file__).parent / "data"
        kpoints_json = datadir / "kpoints.json"
        with kpoints_json.open('r') as fp:
            file_verifies = json.load(fp)
        for f, verifies in file_verifies.items():
            print("Testing {}".format(f))
            fpath = datadir / f
            kpoints = vasp.KPoints.read(fpath)
            for k, v in verifies.items():
                print("- test attribute {}".format(k))
                if isinstance(v, list):
                    self.assertListEqual(v, kpoints.__getattribute__(k))
                else:
                    self.assertEqual(v, kpoints.__getattribute__(k))


class test_chglike(ut.TestCase):
    """test CHG and CHGCAR object"""

    def test_read_chgcar(self):
        """reading the predefined cases"""
        dir_chgcar = pathlib.Path(__file__).parent / "data"
        index_json = dir_chgcar / "chgcar.json"
        with index_json.open('r') as fp:
            verifies = json.load(fp)
        for f, verify in verifies.items():
            print("Testing {}".format(f))
            fpath = dir_chgcar / f
            chgcar = vasp.read_chg(fpath)
            for k, v in verify.items():
                ccv = chgcar.__getattribute__(k)
                print(">> {} ?= {}".format(k, v))
                if isinstance(v, (list, tuple)):
                    self.assertTrue(np.allclose(v, ccv))
                if isinstance(v, (int, float)):
                    self.assertEqual(v, ccv)
            chgcar.export_cube()

    def test_arithmetics(self):
        """addition and subtraction"""
        cell1 = Cell.diamond("C", a=2.0)
        cell2 = Cell.diamond("C", a=1.0)
        data1 = np.ones((2, 3, 4))
        data2 = np.ones((2, 3, 4)) * 2
        data_diff = data2 - data1
        data_add = data2 + data1
        data_another_shape = np.ones((1, 2, 8))
        chg1 = vasp.ChgLike(cell1, data1)
        chg2 = vasp.ChgLike(cell1, data2)
        chg_another_shape = vasp.ChgLike(cell2, data_another_shape)
        chg_diff = chg2 - chg1
        chg_add = chg2 + chg1
        self.assertTrue(np.array_equal(chg_diff.rawdata, data_diff))
        self.assertTrue(np.array_equal(chg_add.rawdata, data_add))
        self.assertRaises(TypeError, chg_another_shape.__sub__, chg1)



class test_incar(ut.TestCase):
    """test editing INCAR"""
    text = "# ALGO = comment\nIALGO = 53\n ALGO = GW0 ;\n" \
        "A = 1 ; ENCUT = 5 ; B = 2 # note\nENCUTGW = 9 ! note\n\nENCUT = 7\n"

    def test_get(self):
        """whole words of the first statement out of comments are matched"""
        incar = vasp.Incar(self.text)
        self.assertEqual(incar.get("ALGO"), "GW0")
        self.assertEqual(incar.get("encut"), "5")
        self.assertEqual(incar.get("ENCUTGW"), "9")
        self.assertEqual(incar.get("B"), "2")
        self.assertIsNone(incar.get("NBANDS"))

    def test_set(self):
        """only the value of first statement is changed, new tag is appended"""
        incar = vasp.Incar(self.text)
        incar.set("ALGO", "Damped")
        incar.set("ENCUT", 6)
        incar.set("ENCUTGW", 10)
        incar.set("NBANDS", 8)
        self.assertEqual(incar.export(),
                         "# ALGO = comment\nIALGO = 53\n ALGO = Damped ;\n"
                         "A = 1 ; ENCUT = 6 ; B = 2 # note\nENCUTGW = 10 ! note\n\n"
                         "ENCUT = 7\nNBANDS = 8\n")

    def test_delete(self):
        """all statements of the tag are deleted, other tags on the line are kept"""
        incar = vasp.Incar(self.text)
        incar.delete("ENCUT")
        self.assertEqual(incar.export(),
                         "# ALGO = comment\nIALGO = 53\n ALGO = GW0 ;\n"
                         "A = 1; B = 2 # note\nENCUTGW = 9 ! note\n\n")
        incar.delete("A")
        self.assertEqual(incar.get("B"), "2")
        self.assertIsNone(incar.get("A"))

    def test_set_npar_kpar(self):
        """tag is skipped when the value is 1"""
        incar = vasp.Incar()
        incar.set_npar_kpar(2, 1)
        self.assertEqual(incar.export(), "NPAR = 2\n")

    def test_read_template(self):
        """placeholders are filled, and raise when any is left"""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = pathlib.Path(tmpdir) / "INCAR"
            path.write_text("ENCUT = _encut_\nPREC = _prec_\nLWANNIER90_RUN = T\n")
            incar = vasp.Incar.read(path, encut=500, prec="Accurate")
            self.assertEqual(incar.get("ENCUT"), "500")
            self.assertEqual(incar.get("LWANNIER90_RUN"), "T")
            self.assertRaises(ValueError, vasp.Incar.read, path, encut=500)

    def test_from_template(self):
        """create from string"""
        incar = vasp.Incar.from_template("ENCUT = _encut_\n", encut=500)
        self.assertEqual(incar.export(), "ENCUT = 500\n")


class test_outcar(ut.TestCase):
    """test reading OUTCAR"""
    text = """ NKPTS =     10   k-points in BZ     NKDIM =     10   number of bands    NBANDS=      8
   NELECT =       8.0000    total number of electrons
  energy without entropy =      -10.00000000  energy(sigma->0) =      -10.00000000
  energy  without entropy=      -10.10000000  energy(sigma->0) =      -10.20000000
  energy  without entropy=      -10.30000000  energy(sigma->0) =      -10.40000000
                            Elapsed time (sec):       12.345
"""

    def test_read(self):
        """read values, where only the double-space energy lines are for ionic steps"""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = pathlib.Path(tmpdir) / "OUTCAR"
            path.write_text(self.text)
            outcar = vasp.Outcar(path)
            self.assertEqual(outcar.nbands, 8)
            self.assertEqual(outcar.nelect, 8.0)
            self.assertEqual(outcar.wall_time, 12.345)
            self.assertEqual(outcar.get_total_energy(), -10.4)
            self.assertEqual(outcar.get_total_energy(0), -10.2)


class test_outcar_qp(ut.TestCase):
    """test reading QP table from OUTCAR"""
    text = """
  band No.  KS-energies  QP-energies   sigma(KS)   V_xc(KS)     V^pw_x(r,r')   Z   occupation Imag(sigma)

      1      -6.0949      -6.3083     -10.6667     -10.3937     -17.3238       0.7818       2.0000  0.1
      2       5.8855       5.4173     -12.0023     -11.4567     -14.5228       0.8581       0.0000  0.1

 k-point   2 :
  band No.  KS-energies  QP-energies   sigma(KS)   V_xc(KS)     V^pw_x(r,r')   Z   occupation Imag(sigma)

      1      -5.0000      -5.5000     -10.0000     -10.3937     -17.3238       0.7818       2.0000  0.1

"""

    def test_table(self):
        """rows of the chosen k-point are returned"""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = pathlib.Path(tmpdir) / "OUTCAR"
            path.write_text(self.text)
            outcar = vasp.Outcar(path)
            self.assertTupleEqual(outcar.get_qp_table(1).shape, (2, 8))
            self.assertEqual(outcar.get_qp_table(1)[1, 2], 5.4173)
            self.assertEqual(outcar.get_qp_table(2)[0, 7], 2.0)
            self.assertRaises(ValueError, outcar.get_qp_table, 3)


class test_read_kpoints(ut.TestCase):
    """test reading k-points of a calculation"""

    def test_vasprun(self):
        """the k-points are read from an unfinished file"""
        text = """<modeling>
 <kpoints>
  <varray name="kpointlist" >
   <v>       0.0  0.0  0.0 </v>
   <v>       0.5  0.0  0.25 </v>
  </varray>
  <varray name="weights" >
   <v>       0.5 </v>
"""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = pathlib.Path(tmpdir) / "vasprun.xml"
            path.write_text(text)
            kpts = vasp.read_vasprun_kpoints(path)
        self.assertTrue(np.array_equal(kpts, [[0.0, 0.0, 0.0], [0.5, 0.0, 0.25]]))

    def test_ibzkpt(self):
        """tetrahedra data at the end are ignored"""
        text = "mesh\n 2\nReciprocal lattice\n 0.0 0.0 0.0 1\n 0.5 0.0 0.0 7\nTetrahedra\n 1 2\n"
        with tempfile.TemporaryDirectory() as tmpdir:
            path = pathlib.Path(tmpdir) / "IBZKPT"
            path.write_text(text)
            kpts, weights = vasp.read_ibzkpt(path)
        self.assertTupleEqual(kpts.shape, (2, 3))
        self.assertListEqual(weights.tolist(), [1, 7])


class test_kpoints_export(ut.TestCase):
    """test exporting KPOINTS"""

    def test_grid(self):
        """export grid mode"""
        kpoints = vasp.KPoints("G", nkgrids=(2, 4, 6), kshifts=(0, 0, 0), comment="grid")
        self.assertEqual(kpoints.export(), "grid\n0\nG\n2 4 6\n0 0 0\n")

    def test_not_implemented(self):
        """other modes cannot be exported"""
        self.assertRaises(NotImplementedError, vasp.KPoints("A", kdense=20).export)

    def test_explicit(self):
        """export explicit k-points in fractional coordinates"""
        kpoints = vasp.KPoints("expl_recp", kpts=[(0.0, 0.0, 0.5), (0.25, 0.0, 0.0)],
                               weights=[1, 0], comment="list")
        self.assertEqual(kpoints.export(), "list\n2\nReciprocal lattice\n"
                         "0.00000000   0.00000000   0.50000000   1\n"
                         "0.25000000   0.00000000   0.00000000   0\n")


class test_read_band_edges(ut.TestCase):
    """test reading band edges from EIGENVAL"""

    def test_edges(self):
        """edges at a k-point do not go beyond the global edges"""
        path = pathlib.Path(__file__).parent / "data" / "EIGENVAL_1"
        bs = vasp.read_eigen(path)[0]
        vbm, cbm = vasp.read_band_edges(path)
        self.assertEqual((vbm, cbm), (bs.vbm, bs.cbm))
        vb, cb = vasp.read_band_edges(path, ik=1)
        self.assertLessEqual(vb, vbm)
        self.assertGreaterEqual(cb, cbm)


class test_results_files(ut.TestCase):
    """test handling result files"""

    def test_clean(self):
        """restart files are kept by default"""
        with tempfile.TemporaryDirectory() as tmpdir:
            workdir = pathlib.Path(tmpdir)
            for name in ("DOSCAR", "WAVECAR", "CHGCAR", "CHGCAR.hf", "W0001.tmp", "POSCAR"):
                (workdir / name).write_text("")
            vasp.clean_results(workdir)
            left = sorted(x.name for x in workdir.iterdir())
            self.assertListEqual(left, ["CHGCAR", "CHGCAR.hf", "POSCAR", "WAVECAR"])
            vasp.clean_results(workdir, restart=True)
            left = sorted(x.name for x in workdir.iterdir())
            self.assertListEqual(left, ["CHGCAR.hf", "POSCAR"])

    def test_warn_changed(self):
        """warn only when the content is different"""
        with tempfile.TemporaryDirectory() as tmpdir:
            workdir = pathlib.Path(tmpdir)
            (workdir / "a").write_text("1")
            (workdir / "b").write_text("1")
            (workdir / "c").write_text("2")
            with warnings.catch_warnings():
                warnings.simplefilter("error")
                vasp.warn_changed(workdir / "a", workdir / "b")
            with self.assertWarns(UserWarning):
                vasp.warn_changed(workdir / "a", workdir / "c")


class test_run_step(ut.TestCase):
    """test running a VASP step with a fake executable"""

    def test_hf_3steps(self):
        """inputs of each step are used, and results are backed up"""
        fake = "import shutil; shutil.copy('INCAR', 'OUTCAR'); print('done')"
        finished = " Elapsed time (sec):  1.0\n"
        with tempfile.TemporaryDirectory() as tmpdir:
            workdir = pathlib.Path(tmpdir)
            for name in ("pbe", "coarse", "hf"):
                (workdir / "INCAR.{}".format(name)).write_text(name + finished)
            (workdir / "KPOINTS.scf").write_text("kpoints")
            vasp.run_hf_3steps([sys.executable, "-c", fake], cwd=workdir)
            for name in ("pbe", "coarse", "hf"):
                self.assertEqual((workdir / "OUTCAR.{}".format(name)).read_text(), name + finished)
                self.assertEqual((workdir / "out.{}".format(name)).read_text(), "done\n")
            self.assertEqual((workdir / "KPOINTS").read_text(), "kpoints")

    def test_tags_and_fixed_chg(self):
        """tags are set in INCAR only, and the charge is copied"""
        fake = "import shutil; shutil.copy('INCAR', 'OUTCAR')"
        finished = " Elapsed time (sec):  1.0\n"
        with tempfile.TemporaryDirectory() as tmpdir:
            workdir = pathlib.Path(tmpdir)
            for name in ("pbe", "coarse", "hf"):
                (workdir / "INCAR.{}".format(name)).write_text(finished)
            (workdir / "KPOINTS.scf").write_text("kpoints")
            (workdir / "CHGCAR.ref").write_text("charge")
            vasp.run_hf_3steps([sys.executable, "-c", fake], cwd=workdir, fixed_chg="CHGCAR.ref")
            self.assertEqual((workdir / "INCAR.hf").read_text(), finished)
            self.assertEqual((workdir / "CHGCAR").read_text(), "charge")
            incar = vasp.Incar.read(workdir / "OUTCAR.pbe")
            self.assertEqual(incar.get("ICHARG"), "11")
            self.assertIsNone(incar.get("ISTART"))
            self.assertEqual(vasp.Incar.read(workdir / "OUTCAR.hf").get("ISTART"), "1")

    def test_unfinished(self):
        """VASP stopped by an internal error with exit code 0 is caught"""
        fake = "open('OUTCAR', 'w').write('VERY BAD NEWS')"
        with tempfile.TemporaryDirectory() as tmpdir:
            workdir = pathlib.Path(tmpdir)
            (workdir / "INCAR.pbe").write_text("pbe")
            self.assertRaises(RuntimeError, vasp.run_step,
                              [sys.executable, "-c", fake], "pbe", cwd=workdir)


if __name__ == "__main__":
    ut.main()
