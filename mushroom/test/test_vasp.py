#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test vasp related utitlies"""
import unittest as ut
import pathlib
import json
import numpy as np

from mushroom import vasp
from mushroom.core.cell import Cell

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
    """test reading vasprunxml"""
    def test_read_eigenval(self):
        """kpoints"""
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


if __name__ == "__main__":
    ut.main()
