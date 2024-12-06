#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test kpoints related functionality"""
import unittest as ut
import numpy as np

from mushroom.core.kpoints import find_k_segments, KPathLinearizer, MPGrid


class test_kpath(ut.TestCase):
    """test the kpath generation"""
    valid_kpts = [
        [
            [0, 0, 0],
            [0, 0, 1],
            [0, 0, 2],
            [0, 0, 3],
            [0, 0, 4],
        ],
        [
            [0, 0, -1],
            [0, 0, 0],
            [0, 0, 1],
            [0, 0, 2],
            [0, 0, 3],
            [0, 0, 4],
        ],
        [
            [0, 2, 4],
            [0, 4, 4],
            [0, 5, 4],
            [0, 6, 4],
        ],
        [
            [4, 2, 3],
            [1, 6, 3],
            [-2, 10, 3],
        ],
        [
            [0, 0, 0],
            [0, 0, 1],
            [0, 0, 2],
            [0, 0, 2],
            [0, 0, 4],
        ],
        [[0, 0, 0], [0, 0, 1], [0, 0, 2], [0, 0, 2], [4, 3, 2], [8, 6, 2],
         [11, 10, 2]],
        [[0, 0, 0], [0, 0, 1], [0, 0, 2], [2, 0, 2], [1, 0, 2], [0, 0, 2]],
        [[0, 0, 0], [0, 0, 1], [0, 0, 2], [1, 0, 2], [2, 0, 2], [3, 0, 2]],
        [[0.000000000000, 0.000000000000, 0.000000000000],
         [0.075000000000, 0.075000000000, 0.150000000000],
         [0.300000000000, 0.300000000000, 0.600000000000],
         [0.375000000000, 0.375000000000, 0.750000000000],
         [0.425000000000, 0.425000000000, 0.650000000000],
         [0.475000000000, 0.475000000000, 0.550000000000],
         [0.500000000000, 0.500000000000, 0.500000000000],
         [0.550000000000, 0.400000000000, 0.550000000000],
         [0.600000000000, 0.300000000000, 0.600000000000],
         [0.625000000000, 0.250000000000, 0.625000000000],
         [0.550000000000, 0.250000000000, 0.700000000000],
         [0.500000000000, 0.250000000000, 0.750000000000],
         [0.700000000000, 0.250000000000, 0.550000000000],
         [0.750000000000, 0.250000000000, 0.500000000000],
         [0.700000000000, 0.200000000000, 0.500000000000],
         [0.600000000000, 0.100000000000, 0.500000000000],
         [0.500000000000, 0.000000000000, 0.500000000000],]
    ]
    valid_ksegs = [
        [(0, 4),],
        [(0, 5),],
        [(0, 3),],
        [(0, 2),],
        [(0, 2), (3, 4)],
        [(0, 2), (3, 5), (5, 6)],
        [(0, 2), (3, 5)],
        [(0, 2), (2, 5)],
        [(0, 3), (3, 6), (6, 9), (9, 11), (11, 13), (13, 16)],
    ]
    valid_xs = [
        [0.0, 1.0, 2.0, 3.0, 4.0],
        [0.0, 1.0, 2.0, 3.0, 4.0, 5.0],
        [0.0, 2.0, 3.0, 4.0],
        [0.0, 5.0, 10.0],
        [0.0, 1.0, 2.0, 2.0, 4.0],
        [0.0, 1.0, 2.0, 2.0, 7.0, 12.0, 17.0],
        [0.0, 1.0, 2.0, 2.0, 3.0, 4.0],
        [0.0, 1.0, 2.0, 3.0, 4.0, 5.0],
        [
            0.0, 0.18371173, 0.73484692, 0.91855865, 1.04103314, 1.16350763,
            1.22474487, 1.34721936, 1.46969385, 1.53093109, 1.63699711,
            1.70770778, 1.9905505, 2.06126118, 2.13197185, 2.27339321,
            2.41481457
        ],
    ]
    valid_spec_xs = [
        [0.0, 4.0],
        [0.0, 5.0],
        [0.0, 4.0],
        [0.0, 10.0],
        [0.0, 2.0, 4.0],
        [0.0, 2.0, 12.0, 17.0],
        [0.0, 2.0, 4.0],
        [0.0, 2.0, 5.0],
        [0.0, 0.91855865, 1.22474487, 1.53093109, 1.70770778, 2.06126118, 2.41481457],
    ]

    def test_find_k_segments(self):
        """find correct k segments"""
        for kpts, ksegs in zip(self.valid_kpts, self.valid_ksegs):
            self.assertListEqual(ksegs, find_k_segments(kpts))

    def test_x(self):
        """check the 1d coordinate of kpath"""
        for kpts, x in zip(self.valid_kpts, self.valid_xs):
            kp = KPathLinearizer(kpts)
            self.assertEqual(len(x), len(kp.x))
            for x1, x2 in zip(x, kp.x):
                self.assertAlmostEqual(x1, x2)

    def test_special_x(self):
        """check the 1d coordinate of kpath"""
        for kpts, spec_x in zip(self.valid_kpts, self.valid_spec_xs):
            kp = KPathLinearizer(kpts)
            self.assertEqual(len(spec_x), len(kp.special_x))
            # alias of special_x
            self.assertEqual(len(spec_x), len(kp.X))
            for x1, x2 in zip(spec_x, kp.special_x):
                self.assertAlmostEqual(x1, x2)

    def test_locate(self):
        kpts_band = [
            [0.0, 0.0, 0.0], [0.5, 0.5, 0.5]
        ]
        kp = KPathLinearizer(kpts_band, recp_latt=[[1, 0, 0], [0, 1, 0], [0, 0, 1]], unify_x=True)
        xs = kp.locate([])
        self.assertListEqual(xs, [])
        xs = kp.locate([[0.25, 0.25, 0.25]])
        xs_ref = [[0.5,]]
        for x, x_ref in zip(xs, xs_ref):
            self.assertListEqual(x, x_ref)


class test_mpgrid(ut.TestCase):
    """test the Monkhorst-Pack grid generation"""

    def test_gamma(self):
        """Gamma only"""
        mp = MPGrid(1, 1, 1)
        self.assertTrue(np.array_equal(mp.kpts, [[0., 0., 0.]]))
        mp = MPGrid(1, 1, 1, shift=[1, 1, 1])
        self.assertTrue(np.array_equal(mp.kpts, [[0.5, 0.5, 0.5]]))

    def test_mp_wo_shift(self):
        """grids without shift"""
        mp = MPGrid(1, 2, 4)
        self.assertTrue(
            np.array_equal(
                mp.kpts,
                np.array([[0., 0., -0.25], [0., 0., 0.], [0., 0., 0.25],
                          [0., 0., 0.5], [0., 0.5, -0.25], [0., 0.5, 0.],
                          [0., 0.5, 0.25], [0., 0.5, 0.5]])))
        self.assertTrue(
            np.array_equal(
                mp.grids,
                np.array([[0, 0., -1], [0, 0, 0], [0, 0, 1], [0, 0, 2],
                          [0, 1, -1], [0, 1, 0], [0, 1, 1], [0, 1, 2]])))


if __name__ == "__main__":
    ut.main()
