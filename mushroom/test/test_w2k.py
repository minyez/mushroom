#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""testing wien2k facilities"""
import json
import pathlib
import unittest as ut
import tempfile

import numpy as np

from mushroom.w2k import (Struct, _energy_kpt_line, read_energy,
                          get_casename, get_inputs)

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
                if isinstance(v, (int, float)):
                    self.assertEqual(objv, v, msg=msg)
                elif isinstance(v, list):
                    self.assertTrue(np.array_equal(objv, v), msg)
            tf = tempfile.NamedTemporaryFile()
            with open(tf.name, 'w') as h:
                s.write(h)
            tf.close()

class test_match_lines(ut.TestCase):
    """test matching Fortran-formatted lines"""
    # pylint: disable=C0301
    def test_match_one_energy_kpt_line(self):
        """kpt line"""
        valid_lines = [
            " 0.000000000000E+00 0.000000000000E+00 0.000000000000E+00         1  1017   113  1.0\n",
            ]
        valid_kpts = [
            [0.0, 0.0, 0.0],
            ]
        valid_nbands = [
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
            natm_ineq, kpts, bs = read_energy(str(fpath))
            self.assertEqual(natm_ineq, verify["natm_ineq"])
            self.assertTrue(np.allclose(kpts, verify["kpts"]))

class test_utilities(ut.TestCase):
    """test utilities for wien2k analysis"""
    testdir = pathlib.Path(__file__).parent / "wien2k_testdir"

    def test_get_casename(self):
        """get the casename"""
        self.assertEqual("fake", get_casename(self.testdir))
        self.assertRaises(FileNotFoundError, get_casename, dirpath=self.testdir,
                          casename="casename_not_exist")
        self.assertEqual("fake", get_casename(dirpath=self.testdir, casename="fake"))
        self.assertEqual("test", get_casename(pathlib.Path(__file__).parent))
                          
    def test_get_inputs(self):
        """get inputs files"""
        self.assertListEqual(get_inputs("struct", dirpath=self.testdir, relative=self.testdir),
                             ["fake.struct",])
        self.assertListEqual(get_inputs("struct", "in1", "inc", "core",
                                        dirpath=self.testdir, relative=True),
                             ["fake.struct", "fake.in1", "fake.inc", "fake.core"])
        self.assertListEqual(get_inputs("struct", dirpath=self.testdir),
                             ["{}.struct".format(self.testdir / "fake"),])

if __name__ == "__main__":
    ut.main()
