#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test math functions"""
import unittest as ut
import numpy as np
try:
    from scipy import special
except ImportError:
    special = None
from mushroom.core.math_func import hyp2f2_1f1_series, rising_factor, general_comb, \
    solid_angle, sph_harm, sph_harm_xyz, gamma_negahalf


class test_math_func(ut.TestCase):
    """test math functions"""

    def test_solid_angle(self):
        """solid angle"""
        self.assertTupleEqual(solid_angle([1, 0, 0]), (0.5 * np.pi, 0.0))
        self.assertTupleEqual(solid_angle([1, 0, 0], polar_positive=False),
                              (0.0, 0.0))
        self.assertTupleEqual(solid_angle([1, 1, 0]),
                              (0.5 * np.pi, 0.25 * np.pi))
        self.assertTupleEqual(solid_angle([1, 1, 0], polar_positive=False),
                              (0.0, 0.25 * np.pi))
        self.assertTupleEqual(solid_angle([1, 0, 1]), (0.25 * np.pi, 0.0))
        self.assertTupleEqual(solid_angle([1, 0, 1], polar_positive=False),
                              (-0.25 * np.pi, 0.0))
        self.assertTupleEqual(solid_angle([0, 1, -1]),
                              (0.75 * np.pi, 0.5 * np.pi))
        self.assertTupleEqual(solid_angle([0, 1, -1], polar_positive=False),
                              (0.25 * np.pi, 0.5 * np.pi))
        self.assertTupleEqual(solid_angle([0, 0, 2]), (0, 0))
        self.assertTupleEqual(solid_angle([0, 0, 2], polar_positive=False),
                              (-0.5 * np.pi, 0))

    def test_gamma_negahalf(self):
        """test Gamma(0.5-n)"""
        ns = np.array([0, 1, 2, 3, 4, 5])
        results = np.array([1.0, -2.0, 4.0/3.0, -8.0/15.0, 16.0/105.0, -32.0/945.0]) * \
                np.sqrt(np.pi)
        for n, gnh in zip(ns, results):
            print(gnh)
            self.assertAlmostEqual(gnh, gamma_negahalf(n))

    def test_sph_harm(self):
        """spherical harmonics"""
        self.assertEqual(np.sqrt(0.25 / np.pi), sph_harm(0, 0, 0, 0))
        self.assertAlmostEqual(0.0, sph_harm(3, 0, np.pi / 2, 0))
        self.assertAlmostEqual(
            -0.41766548929847102656 - 0.22817169672557974236j,
            sph_harm(4, 1, 0.5, 0.5))
        self.assertAlmostEqual(
            -0.030776222708993890287 + 0.021055146776944193288j,
            sph_harm(10, 2, 0.5, -0.3))

    def test_sph_harm_xyz(self):
        """spherical harmonics"""
        self.assertAlmostEqual(0.32569524293385786878,
                               sph_harm_xyz(6, 2, [1, 0, 0]))

    def test_hyp2f2_1f1_series_negax(self):
        """test computing hypergeometric function 2F2 from sum of 1F1 series"""
        if special is None:
            return
        x = np.array([-1.0, -2.0, -3.0])
        hyp2f2s = {
            (0.5, 3.0, 1.5, 3.0):
            0.5 * special.erf(np.sqrt(-x)) / np.sqrt(-x / np.pi),
            (0.5, 3.0, 2.5, 3.0):
            np.array([0.8360276805, 0.7236627387, 0.6428762174]),
            (0.5, 3.0, 2.5, 2.0):
            np.array([0.7691250197, 0.6295236897, 0.5389767245]),
            (1.5, 3.0, 4.5, 1.0):
            np.array([0.3443655255, 0.08500307177, -0.01303472822]),
            (-0.5, 2.0, 0.5, 1.0):
            np.array([2.60835, 3.7242, 4.58888]),
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
            0: [
                1.0,
            ] * len(N),
            1: N,
            1.5:
            np.array([16 / 3, 32 / 3, 512 / 30, 512 / 21, 2048 / 63]) / np.pi,
            2: [1.0, 3.0, 6.0, 10.0, 15.0],
        }
        for k, value in values.items():
            gc = general_comb(N, k)
            print(gc, value)
            self.assertTrue(np.allclose(gc, value))


if __name__ == "__main__":
    ut.main()
