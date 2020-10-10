#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test vasp related utitlies"""
import unittest as ut
import pathlib
import json

from mushroom import vasp

class test_read_doscar(ut.TestCase):
    """test reading in DOSCAR to get a DensityOfStates object"""
    def test_read_testdata(self):
        """read test DOSCARs in data directory"""
        p = pathlib.Path(__file__).parent
        with open(p / "data" / "doscar.json", 'r') as fp:
            verifies = json.load(fp)
        dir_poscar = p / "data"
        for f in dir_poscar.glob(r"DOSCAR_(\d)+"):
            dos = vasp.read_doscar(dosfile=f.relative_to(p))
            verify = verifies[f.name]
            for k, v in verify.items():
                self.assertEqual(dos.__getattribute__(k), v)


if __name__ == "__main__":
    ut.main()
