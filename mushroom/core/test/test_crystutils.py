# -*- coding: utf-8 -*-

import unittest as ut

from mushroom.core.crystutils import (atms_from_sym_nat, axis_list,
                                       periodic_duplicates_in_cell, sym_nat_from_atms)

class test_cell_utils(ut.TestCase):
    """Test the utility functions for ``Cell`` use
    """

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
        self.assertSetEqual(set([1, 2, 3]), set(axis_list(0)))
        self.assertSetEqual(set([1, ]), set(axis_list(1)))
        self.assertSetEqual(set([1, 2]), set(axis_list([1, 2])))

    def test_atms_from_sym_nat(self):
        atms = atms_from_sym_nat(["C", "Al", "F"], [2, 3, 1])
        self.assertListEqual(atms, ["C", "C", "Al", "Al", "Al", "F"])

    def test_sym_nat_from_atms(self):
        sym, nat = sym_nat_from_atms(["C", "Al", "Al", "C", "Al", "F"])
        self.assertListEqual(sym, ["C", "Al", "F"])
        self.assertListEqual(nat, [2, 3, 1])


if __name__ == "__main__":
    ut.main()
