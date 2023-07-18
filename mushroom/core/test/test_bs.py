#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test bandstructure functionality"""
# pylint: disable=C0115,C0116
import json
import os
import unittest as ut

import numpy as np

from mushroom.core.bs import BandStructure as BS
from mushroom.core.bs import BandStructureError as BSErr
from mushroom.core.bs import random_band_structure
from mushroom.core.bs import split_apb, resolve_band_crossing_2band, resolve_band_crossing, left_right_derivative_band
from mushroom.core.constants import EV2RY
from mushroom.core.ioutils import get_matched_files

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
badWeight = [
    1,
]
efermi = 1.0
nspins, nkpts, nbands = np.shape(goodEigen)


class test_BS_no_projection(ut.TestCase):

    def test_raise_inconsistent_eigen_occ(self):
        self.assertRaises(BSErr, BS, badEigen, goodOcc)
        self.assertRaises(BSErr, BS, goodEigen, badOcc)
        self.assertRaises(BSErr, BS, goodEigen, goodOcc, badWeight)

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
        self.assertTupleEqual((3, ), np.shape(bs.ivbm))
        self.assertTupleEqual((nspins, nkpts), np.shape(bs.icbm_sp_kp))
        self.assertTupleEqual((nspins, 2), np.shape(bs.icbm_sp))
        self.assertTupleEqual((3, ), np.shape(bs.icbm))
        self.assertTupleEqual((nspins, nkpts), np.shape(bs.vbm_sp_kp))
        self.assertTupleEqual((nspins, ), np.shape(bs.vbm_sp))
        self.assertTupleEqual((), np.shape(bs.vbm))
        self.assertTupleEqual((nspins, nkpts), np.shape(bs.cbm_sp_kp))
        self.assertTupleEqual((nspins, ), np.shape(bs.cbm_sp))
        self.assertTupleEqual((), np.shape(bs.cbm))
        self.assertTupleEqual((nspins, nkpts), np.shape(bs.direct_gaps()))
        self.assertTupleEqual((nspins, ), np.shape(bs.direct_gap_sp()))
        # direct_gap is a float
        self.assertTupleEqual((), np.shape(bs.direct_gap()))
        self.assertTupleEqual((nspins, ), np.shape(bs.fund_gap_sp()))
        # fund_gap is a float
        self.assertTupleEqual((), np.shape(bs.fund_gap()))
        self.assertTupleEqual((nspins, 2), np.shape(bs.fund_trans_sp()))
        self.assertTupleEqual((2, 2), np.shape(bs.fund_trans()))
        self.assertTupleEqual((nspins, ), np.shape(bs.kavg_gap()))
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
        self.assertTrue(np.array_equal(bs.eigen, np.multiply(goodEigen,
                                                             EV2RY)))
        self.assertEqual(efermi * EV2RY, bs.efermi)
        self.assertEqual(vbm * EV2RY, bs.vbm)

    def test_get_band_indices(self):
        bs = BS(goodEigen, goodOcc, goodWeight, efermi=efermi)
        bs.compute_band_edges()
        self.assertListEqual([
            ivb,
        ], bs.get_band_indices('vbm'))
        self.assertListEqual([ivb - 1, ivb + 1],
                             bs.get_band_indices('vbm-1', 'cbm'))

    def test_get_eigen(self):
        """get eigen values"""
        nsp, nkp, nb = 1, 4, 4
        eigen = np.ones((nsp, nkp, nb))
        bs = BS(eigen)
        self.assertTrue(np.array_equal(np.ones((nsp, nkp, 1)),
                                       bs.get_eigen(0)))
        self.assertTrue(np.array_equal(eigen, bs.get_eigen()))

    def test_gap(self):
        """test gap calculation"""
        nsp, nkp, nb = 1, 4, 4
        gap = 1.0
        # create a gap of 1 eV
        eigen = np.ones((nsp, nkp, nb))
        eigen[:, :, nb // 2:] += gap
        occ = np.zeros((nsp, nkp, nb))
        # occupied
        occ[:, :, :nb // 2] += 1.0
        weight = np.ones(nkp)
        bs = BS(eigen, occ, weight)
        self.assertTrue(
            np.array_equal(bs.direct_gaps(),
                           np.ones((nsp, nkp)) * gap))
        self.assertTrue(
            np.array_equal(bs.direct_gap_sp(),
                           np.ones((nsp, )) * gap))
        self.assertEqual(bs.direct_gap(), gap)
        self.assertTrue(bs.is_gap_direct())

    def test_get_dos(self):
        """test dos generation from band structure"""
        nsp, nkp, nb = 1, 4, 4
        eigen = np.zeros((nsp, nkp, nb * 2))
        eigen[:, :, :nb] = 1.0

    def test_reading_in_good_eigen(self):
        good = 0
        datadir = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                               'data')

        for path in get_matched_files(r'BandStructure_eigen_[\d]+\.json',
                                      datadir):
            with open(path, 'r') as f:
                j = json.load(f)
            shape = j.pop("shape")
            self.assertTupleEqual(np.shape(j["eigen"]), tuple(shape))
            nsp, nkp, nb = shape[:3]
            bs = BS(j["eigen"], efermi=j["efermi"])
            self.assertEqual(bs.fund_gap(), j["fund_gap"])
            self.assertListEqual(bs.ivbm.tolist(), j["ivbm"])
            self.assertListEqual(bs.icbm.tolist(), j["icbm"])
            good += 1
        print("Processed {} good band structure eigenvalues".format(good))


class test_BS_projection(ut.TestCase):

    datadir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')

    def test_reading_in_good_projection(self):
        good = 0
        for path in get_matched_files(r'BandStructure_proj_[\d]+\.json',
                                      self.datadir):
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
            bs = BS(eigen,
                    occ,
                    weight,
                    pwav=j["pwav"],
                    atms=j["atms"],
                    prjs=j["prjs"])
            self.assertListEqual(bs.atms, j["atms"])
            self.assertListEqual(bs.prjs, j["prjs"])
            self.assertTrue(bs.has_proj())
            self.assertTupleEqual((nsp, nkp, nb), bs.get_pwav(0, 0).shape)
            self.assertTupleEqual((nsp, nkp, nb), bs.get_eigen().shape)
            self.assertTupleEqual((nsp, nkp, 1), bs.get_pwav(0, 0, 0).shape)
            self.assertTupleEqual((nsp, nkp, 1), bs.get_eigen(0).shape)
            if nb >= 2:
                self.assertTupleEqual((nsp, nkp, 2),
                                      bs.get_eigen([0, 1]).shape)
                self.assertTupleEqual((nsp, nkp, 2),
                                      bs.get_pwav(0, 0, (0, 1)).shape)
            good += 1
        print("Processed {} good band structure projections".format(good))

    # pylint: disable=R0914
    def test_get_pwav(self):
        nsp, nkp, nb, natm, nprj = 1, 4, 4, 6, 9
        eigen = np.ones((nsp, nkp, nb))
        gap = 1.0
        # create a gap of 1 eV
        eigen[:, :, :nb // 2] += gap
        occ = np.zeros((nsp, nkp, nb))
        # occupied
        occ[:, :, :nb // 2] += 1.0
        weight = np.ones(nkp)
        atms = np.random.choice(["Si", "O", "C"], natm)
        prjs = np.random.choice(["s", "p", "f"], nprj)
        pwav = np.ones((nsp, nkp, nb, natm, nprj))
        bs = BS(eigen, occ, weight)
        self.assertRaises(BSErr, bs.get_pwav)
        # when no atms or prjs is parsed, error will be raised
        bs = BS(eigen, occ, weight, pwav=pwav)
        self.assertRaises(ValueError, bs.get_pwav, atm='Si')
        self.assertRaises(ValueError, bs.get_pwav, atm=['Si', 0])
        self.assertRaises(ValueError, bs.get_pwav, prj='s')
        self.assertRaises(ValueError, bs.get_pwav, prj=[0, 's'])
        bs = BS(eigen, occ, weight, pwav=pwav, atms=atms, prjs=prjs)
        self.assertTrue(
            np.array_equal(bs.get_pwav(0, 0), np.ones((nsp, nkp, nb))))
        self.assertTrue(
            np.array_equal(bs.get_pwav(0, 0, 0), np.ones((nsp, nkp, 1))))
        self.assertTrue(
            np.array_equal(bs.get_pwav([0, 1], [0, 1], 0), 4 * np.ones(
                (nsp, nkp, 1))))
        for at, nat in zip(*np.unique(atms, return_counts=True)):
            self.assertTrue(
                np.array_equal(bs.get_pwav(at, 0), nat * np.ones(
                    (nsp, nkp, nb))))
            self.assertTrue(
                np.array_equal(bs.get_pwav(at, [0, 1]), 2 * nat * np.ones(
                    (nsp, nkp, nb))))
        for pt, npt in zip(*np.unique(prjs, return_counts=True)):
            self.assertTrue(
                np.array_equal(bs.get_pwav(0, pt), npt * np.ones(
                    (nsp, nkp, nb))))
            self.assertTrue(
                np.array_equal(bs.get_pwav([0, 1], pt), 2 * npt * np.ones(
                    (nsp, nkp, nb))))
        # self.assertEqual(gap, bs.effective_gap())
        self.assertIsInstance(bs.effective_gap(), float)


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

    def test_has_proj(self):
        """check randomize with projection"""
        bs = random_band_structure(has_proj=True)
        self.assertIsInstance(bs, BS)


class test_split_apb(ut.TestCase):
    """test splitting of apb"""

    def test_raise(self):
        """raise for whitesapce and missing members"""
        self.assertRaises(ValueError, split_apb, "Fe :3:10")
        self.assertRaises(ValueError, split_apb, "Fe :3")

    def test_correct_splitting(self):
        """correct split of a string"""
        atms, prjs, bands = split_apb("Fe:4:12")
        self.assertListEqual(atms, [
            "Fe",
        ])
        self.assertListEqual(prjs, [
            4,
        ])
        self.assertListEqual(bands, [
            12,
        ])


class test_BS_resolve_crossing(ut.TestCase):

    def test_left_right_derivative_band(self):
        # an ideal 1-segment path, linear dispersion, crossing between kx 0.4 and 0.5
        kx    = [ 0.0,  0.1, 0.2, 0.3, 0.4, 0.5, 0.7, 0.9,  1.1]
        band1 = [ 1.0,  0.9, 0.8, 0.7, 0.6, 0.5, 1.0, 1.4,  1.8]
        band2 = [-0.4, -0.2, 0.0, 0.2, 0.4, 0.6, 0.3, 0.1, -0.1]
        ld, rd = left_right_derivative_band(kx, band1)
        ld_ref = [-1, -1, -1, -1, -1, -1, 2.5, 2, 2]
        rd_ref = [-1, -1, -1, -1, -1, 2.5, 2, 2, 2]
        self.assertTrue(np.allclose(ld, ld_ref))
        self.assertTrue(np.allclose(rd, rd_ref))
        ld, rd = left_right_derivative_band(kx, band2)
        ld_ref = [2, 2, 2, 2, 2, 2, -1.5, -1, -1]
        rd_ref = [2, 2, 2, 2, 2, -1.5, -1, -1, -1]
        self.assertTrue(np.allclose(ld, ld_ref))
        self.assertTrue(np.allclose(rd, rd_ref))

    def test_resolve_two_bands_linear_dispersion(self):
        # an ideal 1-segment path, linear dispersion, crossing between kx 0.4 and 0.5
        kx    = [ 0.0,  0.1, 0.2, 0.3, 0.4, 0.5, 0.7, 0.9,  1.1]
        band1 = [ 1.0,  0.9, 0.8, 0.7, 0.6, 0.5, 1.0, 1.4,  1.8]
        band2 = [-0.4, -0.2, 0.0, 0.2, 0.4, 0.6, 0.3, 0.1, -0.1]
        band1_resolve_ref = [ 1.0,  0.9, 0.8, 0.7, 0.6, 0.5, 0.3, 0.1, -0.1]
        band2_resolve_ref = [-0.4, -0.2, 0.0, 0.2, 0.4, 0.6, 1.0, 1.4,  1.8]
        # band1_res, band2_res = resolve_band_crossing_2band(kx, band1, band2, deriv_thres=3)
        # self.assertTrue(np.allclose(band1_res, band1_resolve_ref))
        # self.assertTrue(np.allclose(band2_res, band2_resolve_ref))

    def test_resolve_two_bands(self):
        datafile = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                'data', 'BandStructure_crossing_0.json')
        with open(datafile, 'r') as f:
            j = json.load(f)
        # entangled bands
        kx = j["kx"]
        band1_en = j["entangled"]["band1"]
        band2_en = j["entangled"]["band2"]
        band1_resolve_ref = j["disentangled"]["band1"]
        band2_resolve_ref = j["disentangled"]["band2"]
        # use the 2-band version
        band1_res, band2_res = resolve_band_crossing_2band(kx, band1_en, band2_en, deriv_thres=5)
        self.assertTrue(np.allclose(band1_res, band1_resolve_ref))
        self.assertTrue(np.allclose(band2_res, band2_resolve_ref))

        # use the general version
        bands = np.array([band1_en, band2_en])
        band1_res, band2_res = resolve_band_crossing(kx, bands, deriv_thres=5)
        self.assertTrue(np.allclose(band1_res, band1_resolve_ref))
        self.assertTrue(np.allclose(band2_res, band2_resolve_ref))


if __name__ == '__main__':
    ut.main()
