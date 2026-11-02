"""text reader checks using small documented layouts"""
from pathlib import Path
import tempfile
import unittest as ut

import numpy as np
from mushroom import librpa


class test_librpa_parsers(ut.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / 'data'

    def test_dimensions(self):
        self.path.write_text('Total number of tasks 4\nMaximumal number of threads 2\n'
                             'Maximal number of threads 3\n| Number of atoms 2\nnfreq = 16\n'
                             '| number of spins 1\n| number of k-points 8\n| number of bands 20\n'
                             '| number of NAOs 12\n===== Begin control parameters =====\n'
                             'libri_chi0_threshold_C = 0.0001\ntask = rpa\n===== End control parameters   =====\n')
        self.assertEqual(librpa.read_librpa_dimension(self.path), dict(n_procs=4, n_threads=3, n_atoms=2,
                         n_freq=16, n_spin=1, n_kpts=8, n_bands=20, n_basis=12,
                         libri_chi0_threshold_C=0.0001, task='rpa'))

    def test_dimensions_missing_controls(self):
        self.path.write_text('Total number of tasks 4\n')
        self.assertEqual(librpa.read_librpa_dimension(self.path), {'n_procs': 4})

    def test_dimensions_truncated_controls(self):
        self.path.write_text('Total number of tasks 4\n===== Begin control parameters =====\ntask = rpa\n')
        self.assertEqual(librpa.read_librpa_dimension(self.path), {'n_procs': 4})

    def test_timing(self):
        self.path.write_text('Total   1 100 90\n  G0W0 quasi-particle 1 50 40\n'
                             '    Load truncated Coulomb 1 5 4\n  Export self-energy in KS basis 1 3 2\n'
                             'librpa finished\n')
        timing = librpa.read_librpa_timing(self.path)
        self.assertEqual(timing['total'], [0, 1, 100, 90])
        self.assertEqual(timing['g0w0_total'], [1, 1, 42, 34])
        self.assertEqual(timing['cal_chi0s'], [-1, 0, 0, 0])
        summary = librpa.read_librpa_timing(self.path, details=True)
        self.assertEqual(summary['total'], [0, 1, 100, 90])
        self.path.write_text('Total   1 100 90\n')
        self.assertIsNone(librpa.read_librpa_timing(self.path))

    def test_empty_timing(self):
        self.path.write_text('')
        self.assertIsNone(librpa.read_librpa_timing(self.path))

    def test_self_energy(self):
        self.path.write_text('2 1 1 2\n0.5\n1.5\n1 2\n3 4\n5 6\n7 8\n')
        omega, sigma = librpa.read_self_energy_imagfreq(self.path)
        np.testing.assert_array_equal(omega, [0.5, 1.5])
        np.testing.assert_array_equal(sigma, [[[[1+2j, 5+6j]]], [[[3+4j, 7+8j]]]])
        self.path.write_text('2 1 1 2\n0.5\n1.5\n1 2\n')
        with self.assertRaises(ValueError):
            librpa.read_self_energy_imagfreq(self.path)

    def test_occupations(self):
        self.path.write_text('kpoints 2\nspins 1\nstates 2\n\nheader\nheader\n1 2.0\n2 0.0\n\n1 1.5\n2 0.5\n')
        np.testing.assert_array_equal(librpa.get_occ_numbers_from_bandout(self.path), [[[2, 0], [1.5, 0.5]]])

    def test_eigenvectors_plain(self):
        self.path.write_text('1\n1 2\n3 4\n5 6\n7 8\n2\n9 10\n11 12\n13 14\n15 16\n')
        data = librpa.read_kgrid_eigenvector(self.path, 2, 2, 1)
        np.testing.assert_array_equal(data[0], [[[1+2j, 5+6j], [3+4j, 7+8j]]])
        np.testing.assert_array_equal(data[1], [[[9+10j, 13+14j], [11+12j, 15+16j]]])
        soc = librpa.read_kgrid_eigenvector(self.path, 4, 1, 1, soc=True)
        np.testing.assert_array_equal(soc[0], [[[1+2j, 5+6j, 3+4j, 7+8j]]])
        with self.assertRaises(ValueError):
            librpa.read_kgrid_eigenvector(self.path, 2, 2, 2, soc=True)
        with self.assertRaises(NotImplementedError):
            librpa.read_kgrid_eigenvector(self.path, 2, 2, 1, binary=True)
        self.path.write_text('invalid\n1 2\n')
        with self.assertRaises(ValueError):
            librpa.read_kgrid_eigenvector(self.path, 2, 2, 1)
