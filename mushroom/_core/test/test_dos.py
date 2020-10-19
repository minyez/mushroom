#!/usr/bin/env python3
# coding = utf-8
"""test for density of states object and methods"""
import unittest as ut
import numpy as np

from mushroom._core.constants import EV2RY
from mushroom._core.dos import DensityOfStates, DosError

goodEgrid = [-4, -3, -2, -1, 0, 1, 2, 3, 4]
badEgrid = [-4, -3, -2, -1, 0, 1]
goodDos = [
    [1.0, 2.0, 3.0, 1.0, 0.0, 0.0, 0.0, 1.0, 2.0],
    [1.0, 2.0, 1.0, 2.0, 0.0, 0.0, 0.0, 2.0, 4.0],
]
badDos1 = [1.0, 2.0, 3.0, 4.0],
badDos2 = [
    [3.0, 4.0],
    [1.0, 2.0],
    [0.0, 0.0],
    [0.0, 3.0]
]
badDos = (badDos1, badDos2)
nspins, nedos = np.shape(goodDos)


class test_dos_initialize(ut.TestCase):

    def test_raise_for_inconsistent_egrid_dos(self):
        """exceptions"""
        for b in badDos:
            self.assertRaisesRegex(DosError, r"Inconsistent shape, *",
                                   DensityOfStates, goodEgrid, b, 0.0)
        self.assertRaisesRegex(DosError, r"Inconsistent shape, *",
                               DensityOfStates, badEgrid, goodDos, 0.0)

    def test_properties(self):
        """basic properties"""
        dos = DensityOfStates(goodEgrid, goodDos, efermi=1.0, unit="ev")
        self.assertFalse(dos.has_pdos())
        self.assertEqual(dos.nedos, nedos)
        self.assertEqual(dos.nspins, nspins)
        self.assertEqual('ev', dos.unit)
        self.assertTrue(np.allclose(goodEgrid, dos.egrid))
        self.assertTrue(np.allclose(goodDos, dos.tdos))
        dos.unit = "ry"
        self.assertAlmostEqual(dos.efermi, EV2RY)
        # None for atms, prjs and pdos when no projection was parsed
        self.assertEqual(None, dos.atms)
        self.assertEqual(0, dos.natms)
        self.assertEqual(None, dos.prjs)
        self.assertEqual(0, dos.nprjs)
        self.assertFalse(None, dos.has_pdos())

    #def test_sum_proj(self):
    #    dos = Dos(goodEgrid, goodDos, efermi=0.0, unit="ev")
    #    # no projection was parsed. empty list
    #    self.assertListEqual([], dos._get_atom_indices(None))
    #    self.assertListEqual([], dos._get_proj_indices(None))
    #    self.assertTrue(np.array_equal(dos.sum_atom_proj_comp(
    #        fail_one=True), np.ones((nedos, nspins))))
    #    # raise for bad fail_one type
    #    self.assertRaisesRegex(TypeError, r"fail_one should be bool type.",
    #                           dos.sum_atom_proj_comp, fail_one=3)


if __name__ == '__main__':
    ut.main()
