#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test vasp related utitlies"""
import unittest as ut
import pathlib
import json
import numpy as np

from mushroom import vasp

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
    """test poscar reader"""

if __name__ == "__main__":
    ut.main()
