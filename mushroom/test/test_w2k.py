#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""testing wien2k facilities"""
import json
import os
import pathlib
import sys
import unittest as ut
import tempfile

import numpy as np

from mushroom.w2k import (Struct, _energy_kpt_line, read_energy,
                          _read_efermi_from_second_to_last_el,
                          get_casename, get_inputs, In1, run_step, write_machines)


class test_struct(ut.TestCase):
    """test struct file processing"""

    def test_read(self):
        """read from test struct files"""
        dir_struct = pathlib.Path(__file__).parent / "data"
        index_json = dir_struct / "struct.json"
        with index_json.open('r') as fp:
            verifies = json.load(fp)
        for f, verify in verifies.items():
            print("Testing {}".format(f))
            fpath = dir_struct / f
            s = Struct.read(str(fpath))
            for k, v in verify.items():
                objv = s.__getattribute__(k)
                msg = "error testing {}: {}, {}".format(k, objv, v)
                if isinstance(v, (int, float, str)):
                    self.assertEqual(objv, v, msg=msg)
                elif k == "atms_types":
                    self.assertListEqual(objv, v)
                elif isinstance(v, list):
                    self.assertIsNone(np.testing.assert_allclose(objv, v), msg)
            tf = tempfile.NamedTemporaryFile()
            with open(tf.name, 'w') as h:
                s.write(h)
            tf.close()

    def test_read_posi(self):
        """positions of hexagonal and rhombohedral lattices are in the basis of latt"""
        dir_struct = pathlib.Path(__file__).parent / "data"
        verifies = {
            "3.struct": [[0.0, 0.0, 0.0], [0.5, 0.5, 0.5],
                         [0.10802134, 0.10802134, 0.10802134],
                         [0.89197866, 0.89197866, 0.89197866]],
            "4.struct": [[1 / 3, 2 / 3, 0.0], [2 / 3, 1 / 3, 0.5],
                         [1 / 3, 2 / 3, 0.382], [2 / 3, 1 / 3, 0.882]],
        }
        for f, posi in verifies.items():
            s = Struct.read(str(dir_struct / f))
            np.testing.assert_allclose(s.get_cell().posi, posi, atol=1e-7)

    def test_write_rhombohedral(self):
        """rhombohedral lattice is unchanged after writing and reading"""
        dir_struct = pathlib.Path(__file__).parent / "data"
        s = Struct.read(str(dir_struct / "3.struct"))
        with tempfile.TemporaryDirectory() as d:
            path = pathlib.Path(d) / "rhombohedral.struct"
            path.write_text(s.export())
            r = Struct.read(str(path))
        np.testing.assert_allclose(r.latt, s.latt, atol=1e-4)
        np.testing.assert_allclose(r.get_cell().posi, s.get_cell().posi, atol=1e-7)

    def test_write_cubic_centered(self):
        """F and B lattices are written in the conventional cubic axes"""
        symops = {"rotations": np.array([np.eye(3, dtype=int)]),
                  "translations": np.zeros((1, 3))}
        for kind in ["F", "B"]:
            s = Struct((8.0, 8.0, 8.0, 90.0, 90.0, 90.0), ["Fe"],
                       [np.array([[0.1, 0.2, 0.3]])], kind=kind, symops=symops)
            lines = s.export().splitlines()
            self.assertEqual(lines[3], "  8.000000  8.000000  8.000000"
                                       " 90.000000 90.000000 90.000000")
            self.assertTrue(lines[4].endswith("X=0.10000000 Y=0.20000000 Z=0.30000000"))
            with tempfile.TemporaryDirectory() as d:
                path = pathlib.Path(d) / "cubic.struct"
                path.write_text(s.export())
                r = Struct.read(str(path))
            np.testing.assert_allclose(r.latt, s.latt)
            np.testing.assert_allclose(r.get_cell().posi, s.get_cell().posi, atol=1e-7)


class test_match_lines(ut.TestCase):
    """test matching Fortran-formatted lines"""

    # pylint: disable=C0301
    def test_match_one_energy_kpt_line(self):
        """kpt line"""
        valid_lines = [
            " 0.000000000000E+00 0.000000000000E+00 0.000000000000E+00         1  1017   113  1.0\n",
            " 0.000000000000E+00 0.000000000000E+00 0.000000000000E+00M           1017   113  1.0\n",
        ]
        valid_kpts = [
            [0.0, 0.0, 0.0],
            [0.0, 0.0, 0.0],
        ]
        valid_nbands = [
            113,
            113,
        ]
        for l, refk, refnb in zip(valid_lines, valid_kpts, valid_nbands):
            kpt_line = _energy_kpt_line.match(l)
            self.assertTrue(kpt_line is not None)
            kpt = list(map(float, [kpt_line.group(1), kpt_line.group(2), kpt_line.group(3)]))
            self.assertTrue(np.allclose(kpt, refk))
            nb = int(kpt_line.group(6))
            self.assertEqual(refnb, nb)


class test_energy(ut.TestCase):
    """test energy file processing"""

    def test_read(self):
        """read from test struct files"""
        dir_energy = pathlib.Path(__file__).parent / "data"
        index_json = dir_energy / "energy.json"
        with index_json.open('r') as fp:
            verifies = json.load(fp)
        for f, verify in verifies.items():
            print("Testing {}".format(f))
            fpath = dir_energy / f
            bs, natm_ineq, kpts, symbols = read_energy(str(fpath))
            self.assertEqual(natm_ineq, verify["natm_ineq"])
            self.assertTrue(np.allclose(kpts, verify["kpts"]))
            if symbols:
                self.assertDictEqual(verify["symbols"], symbols)


class test_utilities(ut.TestCase):
    """test utilities for wien2k analysis"""
    dirname = "w2k_testdir"
    testdir = pathlib.Path(__file__).parent.resolve() / dirname

    def test_get_casename(self):
        """get the casename"""
        self.assertEqual("fake", get_casename(self.testdir))
        self.assertRaises(FileNotFoundError, get_casename, dirpath=self.testdir,
                          casename="casename_not_exist")
        self.assertEqual("fake", get_casename(dirpath=self.testdir, casename="fake"))
        self.assertEqual("test", get_casename(pathlib.Path(__file__).parent))

    def test_get_inputs(self):
        """get inputs files"""
        self.assertTupleEqual(get_inputs("struct", dirpath=self.testdir, relative=self.testdir),
                              ("fake.struct",))
        self.assertTupleEqual(get_inputs("struct", "in1", "inc", "core",
                                         dirpath=self.testdir, relative=True),
                              ("fake.struct", "fake.in1", "fake.inc", "fake.core"))
        self.assertTupleEqual(get_inputs("struct", dirpath=self.testdir),
                              ("{}.struct".format(self.testdir / "fake"),))
        os.chdir(self.testdir.parent)
        self.assertTupleEqual(get_inputs("struct", "in1",
                                         dirpath=self.testdir, relative="CWD"),
                              (f"{self.dirname}/fake.struct", f"{self.dirname}/fake.in1",))

    # pylint: disable=C0301
    def test_read_efermi_from_el(self):
        """test reading efermi"""
        s = "198.98000200.44970  0.44970  0.44970  0.44970  0.44970  0.44970  0.44970  0.44970  0.44970  0.44970  0.44970  0.44970  0.00000"
        self.assertAlmostEqual(0.64971, _read_efermi_from_second_to_last_el(s))


class test_in1(ut.TestCase):
    """test reading in1 """

    def test_read(self):
        """reading existing in1 file"""
        dir_in1 = pathlib.Path(__file__).parent / "data"
        index_json = dir_in1 / "in1.json"
        with index_json.open('r') as fp:
            verifies = json.load(fp)
        for f, verify in verifies.items():
            print("Testing {}".format(f))
            fpath = dir_in1 / f
            s = In1.read(str(fpath))
            for k, v in verify.items():
                if k == "lmax_at":
                    self.assertListEqual(v, [s.lmax_at(iat) for iat in range(s.ntypes)])
                    continue
                if k == "ndiff_at":
                    self.assertListEqual(v, [s.ndiff_at(iat) for iat in range(s.ntypes)])
                    continue
                objv = s.__getattribute__(k)
                msg = "error testing {}: {}, {}".format(k, objv, v)
                if isinstance(v, (str, int, float)):
                    self.assertEqual(objv, v, msg=msg)
                elif isinstance(v, list):
                    self.assertTrue(np.array_equal(objv, v), msg)

# TODO: add qtl and dos reader test


class test_workflow_utilities(ut.TestCase):
    """test utilities for workflows"""

    def test_write_machines(self):
        """k-points are distributed evenly, and the host with no k-point is dropped"""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = pathlib.Path(tmpdir) / ".machines"
            write_machines(path, 3, 7, host="node")
            self.assertEqual(path.read_text(),
                             "2:node\n2:node\n3:node\n\ngranularity:1\nextrafine:1\n")
            write_machines(path, 4, 2, host="node")
            self.assertEqual(path.read_text(),
                             "1:node\n1:node\n\ngranularity:1\nextrafine:1\n")

    def test_run_step(self):
        """raise only for a non-empty error file"""
        empty = "open('lapw1.error', 'w').close()"
        filled = "open('lapw2.error', 'w').write('Error')"
        with tempfile.TemporaryDirectory() as tmpdir:
            run_step([sys.executable, "-c", empty], "out", cwd=tmpdir)
            self.assertRaises(RuntimeError, run_step, [sys.executable, "-c", filled], "out",
                              cwd=tmpdir)


if __name__ == "__main__":
    ut.main()
