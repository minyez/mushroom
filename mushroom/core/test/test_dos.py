#!/usr/bin/env python3
# coding = utf-8
"""test for density of states object and methods"""
import unittest as ut
import tempfile
import numpy as np

from mushroom.core.constants import EV2RY
from mushroom.core.dos import DensityOfStates as DOS
from mushroom.core.dos import split_ap, DosError

goodEgrid = [-4, -3, -2, -1, 0, 1, 2, 3, 4]
badEgrid = [-4, -3, -2, -1, 0, 1]
goodDos = [
    [1.0, 2.0, 3.0, 1.0, 0.0, 0.0, 0.0, 1.0, 2.0],
    [1.0, 2.0, 1.0, 2.0, 0.0, 0.0, 0.0, 2.0, 4.0],
]
badDos1 = [1.0, 2.0, 3.0, 4.0]
badDos2 = [
    [3.0, 4.0],
    [1.0, 2.0],
    [0.0, 0.0],
    [0.0, 3.0]
]
badDos = (badDos1, badDos2)


class test_dos_initialize(ut.TestCase):
    """DOS initialization"""

    def test_raise_for_inconsistent_egrid_dos(self):
        """exceptions"""
        for b in badDos:
            self.assertRaisesRegex(DosError, r"Inconsistent shape, *",
                                   DOS, goodEgrid, b, 0.0)
        self.assertRaisesRegex(DosError, r"Inconsistent shape, *",
                               DOS, badEgrid, goodDos, 0.0)

    def test_properties(self):
        """basic properties"""
        nspins, nedos = np.shape(goodDos)
        dos = DOS(goodEgrid, goodDos, efermi=1.0, unit="ev")
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
        self.assertFalse(dos.has_pdos())
        tf = tempfile.NamedTemporaryFile()
        with open(tf.name, 'w') as h:
            print(dos.export_dos(), file=h)
        tf.close()

    def test_get_pdos(self):
        """test pdos extract"""
        nsp, nedos, natm, nprj = 2, 4, 6, 9
        egrid = np.arange(nedos)
        tdos = np.ones((nsp, nedos))
        atms = np.random.choice(["Si", "O", "C"], natm)
        prjs = np.random.choice(["s", "p", "f"], nprj)
        pdos = np.ones((nsp, nedos, natm, nprj))
        dos = DOS(egrid, tdos)
        self.assertRaises(DosError, dos.get_pdos)
        # when no atms or prjs is parsed, error will be raised
        dos = DOS(egrid, tdos, pdos=pdos)
        self.assertRaises(ValueError, dos.get_pdos, atm='Si')
        self.assertRaises(ValueError, dos.get_pdos, atm=['Si', 0])
        self.assertRaises(ValueError, dos.get_pdos, prj='s')
        self.assertRaises(ValueError, dos.get_pdos, prj=[0, 's'])
        dos = DOS(egrid, tdos, pdos=pdos, atms=atms, prjs=prjs)
        self.assertTrue(np.array_equal(dos.get_pdos(0, 0, 0), np.ones(nedos)))
        self.assertTrue(np.array_equal(dos.get_pdos(), natm * nprj * nsp * np.ones(nedos)))
        self.assertTrue(np.array_equal(dos.get_pdos(0, [0, 1], [0, 1]), 4 * np.ones(nedos)))
        for at, nat in zip(*np.unique(atms, return_counts=True)):
            self.assertTrue(np.array_equal(dos.get_pdos(0, at, 0), nat * np.ones(nedos)))
            self.assertTrue(np.array_equal(dos.get_pdos(0, at, [0, 1]),
                                           2 * nat * np.ones(nedos)))
        for pt, npt in zip(*np.unique(prjs, return_counts=True)):
            self.assertTrue(np.array_equal(dos.get_pdos(0, 0, pt), npt * np.ones(nedos)))
            self.assertTrue(np.array_equal(dos.get_pdos(0, [0, 1], pt),
                                           2 * npt * np.ones(nedos)))

class test_split_ap(ut.TestCase):
    """test split atom-projector string"""
    def test_raise(self):
        """raise for whitespace and wrong number of members"""
        self.assertRaises(ValueError, split_ap, "Fe :3")
        self.assertRaises(ValueError, split_ap, "Fe")
        self.assertRaises(ValueError, split_ap, "Fe:4:5")

    def test_correct_splitting(self):
        """correct split of a string"""
        atms, prjs = split_ap("Fe:4")
        self.assertListEqual(atms, ["Fe",])
        self.assertListEqual(prjs, [4,])

if __name__ == '__main__':
    ut.main()
