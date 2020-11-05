#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test package facilities"""
import unittest as ut

from mushroom.core.pkg import detect_matchfn#, detect

class test_detect(ut.TestCase):
    """detect pacakges"""
    def test_detect_matchfn(self):
        """detect package by filename"""
        fns = {
            "INCAR": "vasp",
            ".": None,
            "MoS2.gpw": "gpaw",
            "diamond.vasp": "vasp",
            "Si.POSCAR": "vasp",
            }
        for fn, pkg in fns.items():
            self.assertEqual(pkg, detect_matchfn(fn),
                             msg=fn)


if __name__ == "__main__":
    ut.main()

