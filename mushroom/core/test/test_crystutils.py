#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""test facilities related to crystal manipulation"""
import contextlib
import io
import unittest as ut
from types import SimpleNamespace

import numpy as np

from mushroom.core import crystutils
from mushroom.core.constants import PI, NAV, ANG2AU
from mushroom.core.crystutils import (atms_from_sym_nat, axis_list, get_volume, get_recp_latt,
                                      periodic_duplicates_in_cell, sym_nat_from_atms,
                                      get_latt_consts_from_latt_vecs,
                                      get_latt_vecs_from_latt_consts, get_density)
from mushroom.core.crystutils import display_symmetry_info


class test_cell_utils(ut.TestCase):
    """Test the utility functions for ``Cell`` use
    """

    def test_latt(self):
        """volume and lattice"""
        # latt = np.array([[1.0, 0.0, 0.0],[0.0, 2.0, 0.0],[0.0, 0.0, 3.0]])
        # self.assertEqual(6.0, get_vol(latt))
        # recp_latt = np.array([[1.0, 0.0, 0.0],[0.0, 1/2, 0.0],[0.0, 0.0, 1/3]]) * 2.0E0 * PI
        # self.assertTrue(np.array_equal(get_recp_latt(latt), recp_latt))
        latt = np.array([[0.0, 3.0, 3.0], [3.0, 0.0, 3.0], [3.0, 3.0, 0.0]])
        # self.assertAlmostEqual(54.0, get_vol(latt))
        recp_latt = np.array([[-1 / 6, 1 / 6, 1 / 6],
                              [1 / 6, -1 / 6, 1 / 6],
                              [1 / 6, 1 / 6, -1 / 6]]) * 2.0E0 * PI
        self.assertTrue(np.allclose(get_recp_latt(latt), recp_latt))
        self.assertAlmostEqual(get_volume(latt), 54.0)

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

    def test_get_latt_consts_from_latt_vecs(self):
        # invalid shapes
        latt = np.array([[2.51000000, 0.00000000, 0.00000000,],
                         [0.00000000, 2.51000000, 0.00000000,]])
        self.assertRaises(ValueError, get_latt_consts_from_latt_vecs, latt)

        latt = np.array([[2.51000000, 0.00000000, 0.00000000,],
                         [0.00000000, 2.51000000, 0.00000000,],
                         [0.00000000, 0.00000000, 6.69000000,]])
        latt_consts = [2.510, 2.510, 6.690, 90.0, 90.0, 90.0]
        converted = get_latt_consts_from_latt_vecs(latt)
        self.assertTrue(np.array_equal(latt_consts, converted))

    def test_get_density(self):
        latt = np.array([[1.0, 0.0, 0.0,],
                         [0.0, 1.0, 0.0,],
                         [0.0, 0.0, 1.0,]]) * 10.0
        atms = ["H",]
        density_n, density_m = get_density(latt, atms, latt_unit="ang")
        self.assertAlmostEqual(density_n, 0.001)
        self.assertAlmostEqual(density_m, 0.001008e27 / NAV)

        latt *= ANG2AU
        density_n, density_m = get_density(latt, atms, latt_unit="au")
        self.assertAlmostEqual(density_n, 0.001)
        self.assertAlmostEqual(density_m, 0.001008e27 / NAV)


class test_symmetry_related(ut.TestCase):

    def test_display_symmetry_info_sort_operations(self):
        rotations = np.array([
            [[1, 1, 0], [0, 0, 0], [0, 0, -1]],
            [[1, 0, 0], [0, 1, 0], [0, 0, -1]],
            [[1, 0, 1], [0, 1, 0], [0, 0, -1]],
        ])
        translations = np.array([[0.1, 0.0, 0.0],
                                 [0.2, 0.0, 0.0],
                                 [0.3, 0.0, 0.0]])
        fake_spglib = SimpleNamespace(get_symmetry_dataset=lambda _: SimpleNamespace(
            number=1, hall="P 1", hall_number=1, international="P1", pointgroup="1",
            rotations=rotations, translations=translations))

        old_spglib = crystutils.spglib
        crystutils.spglib = fake_spglib
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                display_symmetry_info(np.eye(3), [[0.0, 0.0, 0.0]], [1],
                                      sort_operations=True)
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                display_symmetry_info(np.eye(3), [[0.0, 0.0, 0.0]], [1],
                                      print_sym_per_row=True, sort_operations=True)
        finally:
            crystutils.spglib = old_spglib

        values = [float(line.rsplit("|", 1)[1].split()[0])
                  for line in out.getvalue().splitlines() if "|" in line]
        self.assertEqual(values, [0.3, 0.2, 0.1])

    def test_display_symmetry_info(self):
        if crystutils.spglib is None:
            self.skipTest("require spglib")

        # silicon, 227
        latt = np.array([[0.0, 3.0, 3.0], [3.0, 0.0, 3.0], [3.0, 3.0, 0.0]])
        posi = [[0.0, 0.0, 0.0], [0.25, 0.25, 0.25]]
        atms = [14, 14]
        display_symmetry_info(latt, posi, atms)
        atms = ["Si", "Si"]
        display_symmetry_info(latt, posi, atms)

        # RS, 225
        posi = [[0.0, 0.0, 0.0], [0.5, 0.5, 0.5]]
        atms = [11, 17]
        display_symmetry_info(latt, posi, atms)


if __name__ == "__main__":
    ut.main()
