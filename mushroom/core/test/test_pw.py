#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test plane-wave basis"""
import unittest as ut
from mushroom.core.pw import PWBasis
from mushroom.core.unit import ANG2AU, EV2RY

class test_pwbasis(ut.TestCase):
    """planewave construction"""
    def test_initialize(self):
        """test initialization"""
        pw = PWBasis(1, [[1.,0.,0.],[0.,1.,0.],[0.,0.,1.]],
                     eunit="ev", lunit="ang")
        # unit must be converted after initialziation
        self.assertEqual("bohr", pw.lunit)
        self.assertEqual("ry", pw.eunit)
        self.assertAlmostEqual(EV2RY, pw.cutoff)

    def test_get_gamma(self):
        """test gamma point"""
        pw = PWBasis(50, [[5.,0.,0.],[0.,5.,0.],[0.,0.,5.]],
                     eunit="ev", lunit="ang")
        self.assertEqual(93, len(pw.get_ipw(0)))
        self.assertEqual(93, len(pw.get_ipw(0, order_kind='vasp')))

if __name__ == "__main__":
    ut.main()

