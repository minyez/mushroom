"""Analytic quasiparticle corrections and alignment tests."""
import unittest as ut
import numpy as np
from mushroom.core.bs import BandStructure, qp_correction, fit_qp_correction


class test_qp(ut.TestCase):

    def test_fit(self):
        e = np.array([-3., -2, -1, 1, 2, 3])
        occ = e < 0
        de = np.where(occ, .1 + .05 * e, .8 + .1 * e)
        ks = BandStructure(e[None, None], occ[None, None])
        qp = BandStructure((e + de)[None, None])
        ks.unit = 'ry'
        energies, shifts, occupied = qp_correction(ks, qp)
        np.testing.assert_allclose(energies, e)
        np.testing.assert_allclose(shifts, de)
        fit = fit_qp_correction(energies, shifts, occupied)
        for key, slope, intercept in [('vb', .05, .1), ('cb', .1, .8)]:
            self.assertAlmostEqual(fit[key]['slope'], slope)
            self.assertAlmostEqual(fit[key]['intercept'], intercept)
            self.assertEqual(fit[key]['r2'], 1.)
        fit = fit_qp_correction(e[:1], de[:1], occ[:1])
        self.assertIsNone(fit['vb'])
        self.assertIsNone(fit['cb'])

    def test_windows(self):
        ks = BandStructure([[[-2., -1, 2, 3]]], efermi=0.)
        qp = BandStructure([[[.5, 4.]]])
        qp.band_start = 1
        e, de, occ = qp_correction(ks, qp, ref='vbm')
        np.testing.assert_equal(e, [0, 3])
        np.testing.assert_equal(de, [1.5, 2])
        np.testing.assert_equal(occ, [True, False])
        qp.band_start = 6
        with self.assertRaises(ValueError):
            qp_correction(ks, qp)
        with self.assertRaises(ValueError):
            qp_correction(ks, BandStructure(np.ones((2, 1, 4))))
        with self.assertRaises(ValueError):
            qp_correction(BandStructure(ks.eigen), ks)
        with self.assertRaises(ValueError):
            fit_qp_correction([1], [1, 2], [True])
        self.assertLess(fit_qp_correction([1, 2, 3], [1, 4, 2], [True]*3)['vb']['r2'], 1)
