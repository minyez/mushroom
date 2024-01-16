#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import unittest as ut
import pathlib
import json
import os
import tempfile

import numpy as np

from mushroom.aims.gw import read_aims_self_energy_dir, _read_aims_single_sigc_dat


class test_read_self_energy_directory(ut.TestCase):

    def test_read_sing_sigc_dat(self):
        tf = tempfile.NamedTemporaryFile()

        # invalid format, cannot extra frequency
        with open(tf.name, 'w') as h:
            print("0.1-100000006.20", file=h)
        self.assertRaises(ValueError, _read_aims_single_sigc_dat, tf.name)

        # invalid format, cannot separate real and imaginary part due to pathological self energy
        with open(tf.name, 'w') as h:
            print("1.0  0.1-0.2", file=h)
        omegas, sigc = _read_aims_single_sigc_dat(tf.name)
        self.assertEqual(len(omegas), 1)
        self.assertAlmostEqual(0.0, sigc[0].real)
        self.assertAlmostEqual(0.0, sigc[0].imag)

        tf.close()

    def test_kgrid_only_case(self):
        td = tempfile.TemporaryDirectory()
        # spin = 1
        fn = "Sigma.omega.n_3.k_1.dat"
        with open(os.path.join(td.name, fn), 'w') as h:
            print("1.0 1.0 1.0", file=h)
            print("2.0 1.0 1.0", file=h)
            print("3.0 1.0 1.0", file=h)
        omega, state_low, sigc_kgrid, sigc_bands = read_aims_self_energy_dir(td.name)
        self.assertEqual(len(omega), 3)
        self.assertEqual(state_low, 2)
        self.assertTupleEqual(np.shape(sigc_kgrid), (3, 1, 1, 1))
        self.assertEqual(len(sigc_bands), 0)
        td.cleanup()

    def test_band_only_case(self):
        td = tempfile.TemporaryDirectory()
        # spin = 1
        fn = "Sigma.omega.n_1.band_1.k_1.dat"
        with open(os.path.join(td.name, fn), 'w') as h:
            print("1.0 1.0 1.0", file=h)
            print("2.0 1.0 1.0", file=h)
        omega, state_low, sigc_kgrid, sigc_bands = read_aims_self_energy_dir(td.name)
        self.assertEqual(len(omega), 2)
        self.assertEqual(state_low, 0)
        # states and spins
        self.assertTupleEqual(np.shape(sigc_kgrid), (2, 1, 0, 1))
        self.assertEqual(np.size(sigc_kgrid), 0)
        self.assertEqual(len(sigc_bands), 1)
        td.cleanup()

    def test_real_cases(self):
        datadir = pathlib.Path(__file__).parent / "data"
        testcases_json = datadir / "test_self_energy_dir.json"
        with testcases_json.open('r') as h:
            verifies = json.load(h)
        for case, verify in verifies.items():
            sedir = datadir / case
            omega, state_low, sigc_kgrid, sigc_bands = read_aims_self_energy_dir(sedir)
            # print(np.shape(sigc_bands))
            nfreq, nspins, nkpts_grid, nstates = np.shape(sigc_kgrid)
            self.assertEqual(len(omega), nfreq)
            self.assertEqual(nfreq, verify["nfreqs"])
            self.assertEqual(state_low, verify["state_low"])
            self.assertEqual(nspins, verify["nspins"])
            self.assertEqual(nkpts_grid, verify["nkpts_grid"])
            self.assertEqual(nstates, verify["nstates"])

            # bands
            self.assertEqual(len(sigc_bands), verify["nkpaths"])
            self.assertEqual([np.shape(x)[2] for x in sigc_bands], verify["nkpts_band"])


if __name__ == '__main__':
    ut.main()
