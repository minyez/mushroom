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
        for f in dir_doscar.glob(r"DOSCAR_*"):
            dos = vasp.read_doscar(f)
            verify = verifies[f.name]
            print("Testing {}".format(f.name))
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
        for f in dir_procar.glob(r"PROCAR_*"):
            print("Testing {}".format(f.name))
            bs = vasp.read_procar(f)
            verify = verifies[f.name]
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
        for f in dir_xml.glob(r"vasprun.xml_*"):
            verify = verifies[f.name]
            d = vasp.read_xml(*verify.keys(), path=f)
            print("Testing {}".format(f.name))
            for k, v in verify.items():
                self.assertTrue(np.allclose(d[k], v))


if __name__ == "__main__":
    ut.main()
