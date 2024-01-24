# -*- coding: utf-8 -*-

import unittest as ut

import numpy as np

from mushroom.core.eos import get_eos


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


if __name__ == '__main__':
    ut.main()
