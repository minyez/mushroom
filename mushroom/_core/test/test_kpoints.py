#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test kpoints related functionality"""
import unittest as ut

from mushroom._core.kpoints import find_k_segments, KPath

class test_kpath(ut.TestCase):
    """test the kpath generation"""
    valid_kpts = [
        [[0, 0, 0], [0, 0, 1], [0, 0, 2], [0, 0, 3], [0, 0, 4],],
        [[0, 0, -1], [0, 0, 0], [0, 0, 1], [0, 0, 2], [0, 0, 3], [0, 0, 4],],
        [[0, 2, 4], [0, 4, 4], [0, 5, 4], [0, 6, 4],],
        [[4, 2, 3], [1, 6, 3], [-2, 10, 3],],
        [[0, 0, 0], [0, 0, 1], [0, 0, 2], [0, 0, 2], [0, 0, 4],],
        [[0, 0, 0], [0, 0, 1], [0, 0, 2], [0, 0, 2], [4, 3, 2], [8, 6, 2], [11, 10, 2]],
        ]
    valid_ksegs = [
        [(0, 4),],
        [(0, 5),],
        [(0, 3),],
        [(0, 2),],
        [(0, 2), (3, 4)],
        [(0, 2), (3, 5), (5, 6)],
        ]
    valid_xs = [
        [0.0, 1.0, 2.0, 3.0, 4.0],
        [0.0, 1.0, 2.0, 3.0, 4.0, 5.0],
        [0.0, 2.0, 3.0, 4.0],
        [0.0, 5.0, 10.0],
        [0.0, 1.0, 2.0, 2.0, 4.0],
        [0.0, 1.0, 2.0, 2.0, 7.0, 12.0, 17.0],
        ]

    def test_find_k_segments(self):
        """find correct k segments"""
        for kpts, ksegs in zip(self.valid_kpts, self.valid_ksegs):
            self.assertListEqual(ksegs, find_k_segments(kpts))

    def test_kpath_class(self):
        for kpts, xs in zip(self.valid_kpts, self.valid_xs):
            kp = KPath(kpts)
            self.assertListEqual(xs, kp.x)

if __name__ == "__main__":
    ut.main()
