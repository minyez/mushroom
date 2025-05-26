# -*- coding: utf-8 -*-

import unittest as ut

import numpy as np

from mushroom.core.eos import get_eos, fit_eos


class test_eos(ut.TestCase):

    def test_get_eos(self):
        self.assertRaises(KeyError, get_eos, "non-existing-eos-name")
        _, _, nparams = get_eos("m")
        self.assertEqual(nparams, 4)
        _, _, nparams = get_eos("bm")
        self.assertEqual(nparams, 4)

    def test_murnaghan(self):
        eos_m, _, _ = get_eos("m")

        v = np.array([1.0,])
        e = eos_m(v, 1.0, 1.0, 1.0, 2.0)
        e_target = np.array([1.0,])
        self.assertTrue(np.allclose(e, e_target))

    def test_birch_murnaghan(self):
        eos_bm, _, _ = get_eos("bm")

        v = np.array([0.125,])
        e = eos_bm(v, 20.0, 1.0, 1.0, 2.0)
        e_target = np.array([-0.25,])
        print(e - e_target)
        self.assertTrue(np.allclose(e, e_target))

    def test_fit_eos(self):
        vols = [42.5085, 44.0618, 45.6524, 47.2416,
                48.7872, 50.4070, 51.9369, 53.4974,
                55.1323, 56.6674, ]
        enes = [-180983.629411593, -180983.842894495, -180983.984378379, -180984.061636657,
                -180984.086175805, -180984.067814036, -180984.016290385, -180983.935606039,
                -180983.826107542, -180983.704338505, ]
        self.assertRaises(ValueError, fit_eos, "bm", vols, enes, initial_guess=[])
        popt, r2, e = fit_eos("bm", vols, enes)
        self.assertAlmostEqual(popt[0], -180984.08619939)
        self.assertAlmostEqual(popt[1], 48.88650907)
        self.assertAlmostEqual(popt[2], 0.82934823)
        self.assertAlmostEqual(popt[3], 5.01799721)


if __name__ == '__main__':
    ut.main()
