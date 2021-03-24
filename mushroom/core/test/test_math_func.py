#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test math functions"""
import unittest as ut
import numpy as np
try:
    from scipy import special
except ImportError:
    special = None
from mushroom.core.math_func import hyp2f2_1f1_series, rising_factor, general_comb

class test_math_func(ut.TestCase):
    """test math functions"""
    def test_hyp2f2_1f1_series_negax(self):
        """test computing hypergeometric function 2F2 from sum of 1F1 series"""
        if special is None:
            return
        x = np.array([-1.0, -2.0, -3.0])
        hyp2f2s = {
            (0.5, 3.0, 1.5, 3.0): 0.5*special.erf(np.sqrt(-x))/np.sqrt(-x/np.pi),
            (0.5, 3.0, 2.5, 3.0): np.array([0.8360276805, 0.7236627387, 0.6428762174]),
            (0.5, 3.0, 2.5, 2.0): np.array([0.7691250197, 0.6295236897, 0.5389767245]),
            (1.5, 3.0, 4.5, 1.0): np.array([0.3443655255, 0.08500307177, -0.01303472822]),
            (-0.5, 2.0, 0.5, 1.0): np.array([2.60835, 3.7242, 4.58888]),
            }
        for ab, value in hyp2f2s.items():
            hyp2f2 = hyp2f2_1f1_series(*ab, x)
            print(value, hyp2f2)
            self.assertTrue(np.allclose(hyp2f2, value))

    def test_rising_fator(self):
        """test rising factor"""
        if special is None:
            return
        N = [2, 3, 4, 5]
        rfs = {
            0: [1.0, 1.0, 1.0, 1.0],
            1: N,
            2: [6.0, 12.0, 20.0, 30.0],
            }
        for k, value in rfs.items():
            rf = rising_factor(N, k)
            self.assertTrue(np.allclose(rf, value))

    def test_general_comb(self):
        """test general combination number"""
        if special is None:
            return
        N = [2, 3, 4, 5, 6]
        values = {
            0: [1.0,] * len(N),
            1: N,
            1.5: np.array([16/3, 32/3, 512/30, 512/21, 2048/63])/np.pi,
            2: [1.0, 3.0, 6.0, 10.0, 15.0],
            }
        for k, value in values.items():
            gc = general_comb(N, k)
            print(gc, value)
            self.assertTrue(np.allclose(gc, value))

if __name__ == "__main__":
    ut.main()
