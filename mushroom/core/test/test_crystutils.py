#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""test facilities related to crystal manipulation"""
import unittest as ut
import numpy as np
from mushroom.core.constants import PI
from mushroom.core.crystutils import (atms_from_sym_nat, axis_list, get_recp_latt,
                                      periodic_duplicates_in_cell, sym_nat_from_atms,
                                      get_latt_vecs_from_latt_consts)

class test_cell_utils(ut.TestCase):
    """Test the utility functions for ``Cell`` use
    """
    def test_latt(self):
        """volume and lattice"""
        #latt = np.array([[1.0, 0.0, 0.0],[0.0, 2.0, 0.0],[0.0, 0.0, 3.0]])
        #self.assertEqual(6.0, get_vol(latt))
        #recp_latt = np.array([[1.0, 0.0, 0.0],[0.0, 1/2, 0.0],[0.0, 0.0, 1/3]]) * 2.0E0 * PI
        #self.assertTrue(np.array_equal(get_recp_latt(latt), recp_latt))
        latt = np.array([[0.0, 3.0, 3.0],[3.0, 0.0, 3.0],[3.0, 3.0, 0.0]])
        #self.assertAlmostEqual(54.0, get_vol(latt))
        recp_latt = np.array([[-1/6, 1/6, 1/6],[1/6, -1/6, 1/6],[1/6, 1/6, -1/6]]) * 2.0E0 * PI
        self.assertTrue(np.allclose(get_recp_latt(latt), recp_latt))

    def test_periodic_duplicates_in_cell(self):
        """test the output of duplicate"""

        dupcs, n = periodic_duplicates_in_cell([0.2, 0.4, 0.8])
        self.assertEqual(1, n)
        self.assertTupleEqual(([0.2, 0.4, 0.8],), dupcs)
        dupcs, n = periodic_duplicates_in_cell([0.2, 0.4, 0])
        self.assertEqual(2, n)
        self.assertTupleEqual(([0.2, 0.4, 0], [0.2, 0.4, 1.0]), dupcs)
        dupcs, n = periodic_duplicates_in_cell([0, 0.4, 0])
        self.assertEqual(4, n)
        self.assertTupleEqual(([0, 0.4, 0], [1.0, 0.4, 0], [0, 0.4, 1.0], [1.0, 0.4, 1.0]), dupcs)
        dupcs, n = periodic_duplicates_in_cell([0, 0, 0])
        self.assertEqual(8, n)
        self.assertTupleEqual(([0, 0, 0], [1.0, 0, 0], [0, 1.0, 0], [1.0, 1.0, 0], [0, 0, 1.0],
                               [1.0, 0, 1.0], [0, 1.0, 1.0], [1.0, 1.0, 1.0]), dupcs)
        self.assertRaises(AssertionError, periodic_duplicates_in_cell, [1.0, 0.0, 0.0])
        self.assertRaises(AssertionError, periodic_duplicates_in_cell, [1.1, 0.0, 0.0])

    def test_axis_list(self):
        """get axis list corresponding to axis token"""
        self.assertSetEqual(set([1, 2, 3]), set(axis_list(0)))
        self.assertSetEqual(set([1, ]), set(axis_list(1)))
        self.assertSetEqual(set([1, 2]), set(axis_list([1, 2])))

    def test_atms_from_sym_nat(self):
        """atoms list from symbols and number of atoms in each type"""
        atms = atms_from_sym_nat(["C", "Al", "F"], [2, 3, 1])
        self.assertListEqual(atms, ["C", "C", "Al", "Al", "Al", "F"])

    def test_sym_nat_from_atms(self):
        """symbols and number of atoms in each type from atoms list"""
        sym, nat = sym_nat_from_atms(["C", "Al", "Al", "C", "Al", "F"])
        self.assertListEqual(sym, ["C", "Al", "F"])
        self.assertListEqual(nat, [2, 3, 1])

    def test_get_latt_vecs_from_latt_consts(self):
        """test lattice vectors"""
        latt_consts = [2.510, 2.510, 6.690, 90.0, 90.0, 90.0]
        latt = np.array([[2.51000000, 0.00000000, 0.00000000,],
                         [0.00000000, 2.51000000, 0.00000000],
                         [0.00000000, 0.00000000, 6.69000000]])
        converted = get_latt_vecs_from_latt_consts(*latt_consts)
        self.assertTrue(np.array_equal(latt, converted))
        latt_consts = [2.510, 2.510, 6.690, 90.0, 90.0, 120.0]
        latt = np.array([[2.51000000, 0.00000000, 0.00000000,],
                         [-1.25500000, 2.17372400, 0.00000000],
                         [0.00000000, 0.00000000, 6.69000000]])
        converted = get_latt_vecs_from_latt_consts(*latt_consts)
        self.assertTrue(np.array_equal(latt, converted))


if __name__ == "__main__":
    ut.main()
