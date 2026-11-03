"""Tests for program-independent band data helpers."""
import unittest as ut
import numpy as np
from mushroom.core.bs import BandStructure, get_energy_reference
from mushroom.core.kpoints import format_ksymbols, split_kpath_breaks


class test_references(ut.TestCase):

    def test_references(self):
        bs = BandStructure([[[-3, -1, 2, 4], [-2, 0, 3, 5]]],
                           [[[1, 1, 0, 0], [1, 1, 0, 0]]], efermi=1.)
        for ref, expected in [(None, 0), ("none", 0), (0, 0), (2.3, 2.3),
                              ("vbm", 0), ("cbm", 2), ("ef", 1), ("efermi", 1),
                              ("fermi", 1), ("vbm_0", -1), ("0:1:cbm+1", 5),
                              ("0:0:1", -1), ("vbm_-1", 0), ("0:-1:cbm", 3)]:
            self.assertEqual(get_energy_reference(bs, ref), expected)
        with self.assertRaisesRegex(ValueError, "is:ik:ib"):
            get_energy_reference(bs, "bad")
        with self.assertRaisesRegex(ValueError, "Fermi"):
            get_energy_reference(BandStructure(bs.eigen), "ef")

    def test_symbols(self):
        syms = ["GAMMA", "X", "K|U", "L", "\\gamma", "Gamma|X", "$L$"]
        self.assertEqual(format_ksymbols(syms, "plt"),
                         ["$\\Gamma$", "X", "K|U", "L", "$\\Gamma$", "$\\Gamma$|X", "$L$"])
        self.assertEqual(format_ksymbols(syms[:4], "grace"), ["\\Gamma", "X", "K|U", "L"])
        self.assertIsNone(format_ksymbols(None, "plt"))
        with self.assertRaises(ValueError):
            format_ksymbols(syms, "bad")
        self.assertEqual(split_kpath_breaks([0, 1, 2, 3], syms[:4]), ([2], ["K|U"]))
        self.assertEqual(split_kpath_breaks([], None), ([], []))
