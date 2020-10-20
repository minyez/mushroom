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
        p = pathlib.Path(__file__).parent
        with open(p / "data" / "doscar.json", 'r') as fp:
            verifies = json.load(fp)
        dir_doscar = p / "data"
        for f, verify in verifies.items():
            print("Testing {}".format(f))
            dos = vasp.read_doscar(dir_doscar / f)
            for k, v in verify.items():
                self.assertEqual(dos.__getattribute__(k), v)

class test_read_procar(ut.TestCase):
    """test reading in PROCAR to get a BandStructure object"""
    def test_read_testdata(self):
        """read test PROCARs in data directory"""
        p = pathlib.Path(__file__).parent
        with open(p / "data" / "procar.json", 'r') as fp:
            verifies = json.load(fp)
        dir_procar = p / "data"
        for f, verify in verifies.items():
            print("Testing {}".format(f))
            bs, _ = vasp.read_procar(dir_procar / f)
            for k, v in verify.items():
                self.assertEqual(bs.__getattribute__(k), v)

class test_read_xml(ut.TestCase):
    """test reading vasprunxml"""
    def test_read_kpts(self):
        """kpoints"""
        p = pathlib.Path(__file__).parent
        with open(p / "data" / "vasprunxml.json", 'r') as fp:
            verifies = json.load(fp)
        dir_xml = p / "data"
        for f, verify in verifies.items():
            print("Testing {}".format(f))
            d = vasp.read_xml(*verify.keys(), path=dir_xml/f)
            for k, v in verify.items():
                self.assertTrue(np.allclose(d[k], v))


class test_eigenval(ut.TestCase):
    """test reading vasprunxml"""
    def test_read_eigenval(self):
        """kpoints"""
        p = pathlib.Path(__file__).parent
        with open(p / "data" / "eigenval.json", 'r') as fp:
            verifies = json.load(fp)
        dir_eigen = p / "data"
        for f, verify in verifies.items():
            print("Testing {}".format(f))
            bs, natms, kpoints = vasp.read_eigen(path=dir_eigen/f)
            self.assertEqual(natms, verify.pop("natms"))
            for k, v in verify.items():
                bsv = bs.__getattribute__(k)
                print(">> {} ?= {}".format(k, v))
                self.assertTrue(np.allclose(bsv, v))


if __name__ == "__main__":
    ut.main()
