#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test bandstructure functionality"""
# pylint: disable=C0115,C0116
import json
import os
import unittest as ut

import numpy as np

from mushroom.core.bs import BandStructure as BS
from mushroom.core.bs import BandStructureError as BSE
from mushroom.core.bs import random_band_structure
from mushroom.core.constants import EV2RY
from mushroom.core.ioutils import get_matched_files

# pylint: disable=bad-whitespace
goodEigen = [
    [
        [1, 2, 3],
        [11, 22, 33],
    ],
]
badEigen = [[100, 102, 103], [210, 212, 213]]
goodOcc = [
    [
        [1.0, 1.0, 0.0],
        [1.0, 1.0, 0.0],
    ],
]
badOcc = [[1.0, 1.0, 0.0], [1.0, 1.0, 0.0]]
ivb = 1
goodWeight = [1, 4]
badWeight = [1, ]
efermi = 1.0
nspins, nkpts, nbands = np.shape(goodEigen)


class test_BS_no_projection(ut.TestCase):

    def test_raise_inconsistent_eigen_occ(self):
        self.assertRaises(BSE, BS, badEigen, goodOcc)
        self.assertRaises(BSE, BS, goodEigen, badOcc)
        self.assertRaises(BSE, BS, goodEigen, goodOcc, badWeight)

    def test_properties(self):
        bs = BS(goodEigen, goodOcc, goodWeight, efermi=efermi)
        bs.compute_band_edges()
        self.assertTrue(np.allclose(goodEigen, bs.eigen))
        self.assertTrue(np.allclose(goodOcc, bs.occ))
        self.assertEqual(bs.nspins, nspins)
        self.assertEqual(bs.nkpts, nkpts)
        self.assertEqual(bs.nbands, nbands)
        self.assertTupleEqual((nspins, nkpts), np.shape(bs.ivbm_sp_kp))
        self.assertTupleEqual((nspins, 2), np.shape(bs.ivbm_sp))
        self.assertTupleEqual((3,), np.shape(bs.ivbm))
        self.assertTupleEqual((nspins, nkpts), np.shape(bs.icbm_sp_kp))
        self.assertTupleEqual((nspins, 2), np.shape(bs.icbm_sp))
        self.assertTupleEqual((3,), np.shape(bs.icbm))
        self.assertTupleEqual((nspins, nkpts), np.shape(bs.vbm_sp_kp))
        self.assertTupleEqual((nspins,), np.shape(bs.vbm_sp))
        self.assertTupleEqual((), np.shape(bs.vbm))
        self.assertTupleEqual((nspins, nkpts), np.shape(bs.cbm_sp_kp))
        self.assertTupleEqual((nspins,), np.shape(bs.cbm_sp))
        self.assertTupleEqual((), np.shape(bs.cbm))
        self.assertTupleEqual((nspins, nkpts), np.shape(bs.direct_gap()))
        self.assertTupleEqual((nspins,), np.shape(bs.fund_gap()))
        self.assertTupleEqual((nspins, 2), np.shape(bs.fund_trans()))
        self.assertTupleEqual((nspins,), np.shape(bs.kavg_gap()))
        # empty properties when initialized without projections
        self.assertTrue(bs.atms is None)
        self.assertTrue(bs.prjs is None)
        self.assertTrue(bs.pwav is None)
        self.assertFalse(bs.has_proj())
        # unit conversion
        self.assertTrue(np.array_equal(bs.eigen, goodEigen))
        self.assertEqual(efermi, bs.efermi)
        vbm = bs.vbm
        bs.unit = "ry"
        self.assertTrue(np.array_equal(bs.eigen,
                                       np.multiply(goodEigen, EV2RY)))
        self.assertEqual(efermi * EV2RY, bs.efermi)
        self.assertEqual(vbm * EV2RY, bs.vbm)

    def test_get_band_indices(self):
        bs = BS(goodEigen, goodOcc, goodWeight, efermi=efermi)
        bs.compute_band_edges()
        self.assertListEqual([ivb, ], bs.get_band_indices('vbm'))
        self.assertListEqual(
            [ivb-1, ivb+1], bs.get_band_indices('vbm-1', 'cbm'))
    
    #def test_get_dos(self):
    #    bs = BS(goodEigen, goodOcc, goodWeight, efermi=efermi)
    #    bs.get_dos()


class test_BS_projection(ut.TestCase):

    datadir = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           'data')

    def test_reading_in_good_projection(self):
        good = 0
        for path in get_matched_files(self.datadir, r'Bandstructure_proj_[\d]+\.json'):
            with open(path, 'r') as f:
                j = json.load(f)
            shape = j.pop("shape")
            self.assertTupleEqual(np.shape(j["pwav"]), tuple(shape))
            # as occ is randomized, there are cases that warnings infinity CBM
            # it is totally okay.
            nsp, nkp, nb = shape[:3]
            eigen = np.random.random(shape[:3])
            occ = np.random.choice([0.0, 1.0], shape[:3])
            weight = np.random.random(shape[1])
            bs = BS(eigen, occ, weight, pwav=j["pwav"], atms=j["atms"], prjs=j["prjs"])
            self.assertListEqual(bs.atms, j["atms"])
            self.assertListEqual(bs.prjs, j["prjs"])
            self.assertTrue(bs.has_proj())
            self.assertTupleEqual((nsp, nkp, nb), bs.get_pwav(0, 0).shape)
            self.assertTupleEqual((nsp, nkp, nb), bs.get_eigen().shape)
            self.assertTupleEqual((nsp, nkp, 1), bs.get_pwav(0, 0, 0).shape)
            self.assertTupleEqual((nsp, nkp, 1), bs.get_eigen(0).shape)
            if nb >= 2:
                self.assertTupleEqual((nsp, nkp, 2), bs.get_eigen([0, 1]).shape)
                self.assertTupleEqual((nsp, nkp, 2), bs.get_pwav(0, 0, (0, 1)).shape)
            good += 1
        print("Processed {} good band structure projections".format(good))

    # pylint: disable=R0914
    def test_get_pwav(self):
        nsp, nkp, nb, natm, nprj = 1, 4, 5, 6, 9
        eigen = np.ones((nsp, nkp, nb))
        occ = np.ones((nsp, nkp, nb))
        weight = np.ones(nkp)
        atms = np.random.choice(["Si", "O", "C"], natm)
        prjs = np.random.choice(["s", "p", "f"], nprj)
        pwav = np.ones((nsp, nkp, nb, natm, nprj))
        bs = BS(eigen, occ, weight, pwav=pwav, atms=atms, prjs=prjs)
        self.assertTrue(np.array_equal(bs.get_pwav(0, 0), np.ones((nsp, nkp, nb))))
        self.assertTrue(np.array_equal(bs.get_pwav(0, 0, 0), np.ones((nsp, nkp, 1))))
        self.assertTrue(np.array_equal(bs.get_pwav([0, 1], [0, 1], 0), 4 * np.ones((nsp, nkp, 1))))
        for at, nat in zip(*np.unique(atms, return_counts=True)):
            self.assertTrue(np.array_equal(bs.get_pwav(at, 0), nat * np.ones((nsp, nkp, nb))))
            self.assertTrue(np.array_equal(bs.get_pwav(at, [0, 1]),
                                           2 * nat * np.ones((nsp, nkp, nb))))
        for pt, npt in zip(*np.unique(prjs, return_counts=True)):
            self.assertTrue(np.array_equal(bs.get_pwav(0, pt), npt * np.ones((nsp, nkp, nb))))
            self.assertTrue(np.array_equal(bs.get_pwav([0, 1], pt),
                                           2 * npt * np.ones((nsp, nkp, nb))))


class test_BS_randomize(ut.TestCase):
    """Test if the random band structure behaves as expected
    """
    n = 10

    def test_semiconductor(self):
        """check random-generated semiconducotr-like band"""
        ri = np.random.randint
        for _i in range(self.n):
            ns = ri(1, 2)
            nk = ri(3, 31)
            nb = ri(10, 41)
            bs = random_band_structure(ns, nk, nb, is_metal=False)
            self.assertEqual(bs.nspins, ns)
            self.assertEqual(bs.nkpts, nk)
            self.assertEqual(bs.nbands, nb)
            self.assertFalse(bs.is_metal())
            self.assertTrue(np.all(bs.fund_gap() > 0))

    def test_metal(self):
        """check random-generated metal-like band"""
        ri = np.random.randint
        ns = ri(1, 2)
        nk = ri(3, 31)
        nb = ri(10, 41)
        for _i in range(self.n):
            bs = random_band_structure(ns, nk, nb, is_metal=True)
            self.assertTrue(bs.is_metal())


if __name__ == '__main__':
    ut.main()
