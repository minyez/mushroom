#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import unittest as ut
import pathlib
import os
import tempfile
import json


from mushroom.aims.species import Species
from mushroom.aims.species import get_num_obfs, get_l_nrad
from mushroom.aims.species import _SPECIES_DEFAULTS_ENV, \
    search_basis_directories, get_species_defaults_directory, get_basis_directory_from_alias, \
    get_species_filepaths


def _check_if_species_defaults_set():
    """return True, if species_defaults is not available"""
    try:
        species_defaults = os.environ[_SPECIES_DEFAULTS_ENV]
    except KeyError:
        try:
            from mushroom.__config__ import aims_species_defaults as species_defaults
        except ImportError:
            print("Environment variable {} not set, skip species directory test".format(_SPECIES_DEFAULTS_ENV))
            return True
    return False


class test_species_utils(ut.TestCase):

    def test_species_default(self):
        species_defaults_orig = None
        try:
            species_defaults_orig = os.environ[_SPECIES_DEFAULTS_ENV]
            del os.environ[_SPECIES_DEFAULTS_ENV]
        except KeyError:
            pass

        try:
            from mushroom.__config__ import aims_species_defaults as species_defaults
        except ImportError:
            self.assertRaises(KeyError, get_species_defaults_directory)

        os.environ[_SPECIES_DEFAULTS_ENV] = "non-exist"
        self.assertRaises(ValueError, get_species_defaults_directory)
        del os.environ[_SPECIES_DEFAULTS_ENV]

        if species_defaults_orig is not None:
            os.environ[_SPECIES_DEFAULTS_ENV] = species_defaults_orig

    def test_search_basis_diretories(self):
        # test can be done without an existing aims directory
        self.assertRaises(ValueError, search_basis_directories, "some/random/path/should/not/exist")
        self.assertListEqual([], search_basis_directories("some/random/path/should/not/exist", False))
        if _check_if_species_defaults_set():
            return
        paths = search_basis_directories()
        self.assertIn("defaults_2010/tight", paths)

    def test_alias(self):
        self.assertRaises(ValueError, get_basis_directory_from_alias, "unknown")
        self.assertEqual(get_basis_directory_from_alias("tight"), "defaults_2020/tight")
        self.assertEqual(get_basis_directory_from_alias("nao-j-2"), "NAO-J-n/NAO-J-2")
        self.assertEqual(get_basis_directory_from_alias("aug-cc-pvdz"),
                         "non-standard/gaussian_tight_770/aug-cc-pVDZ")
        self.assertEqual(get_basis_directory_from_alias("nao-vcc-2z"), "NAO-VCC-nZ/NAO-VCC-2Z")

    def test_get_specie_filename(self):
        self.assertRaises(ValueError, get_species_filepaths,
                          "unknown", "Ne", species_defaults="path/to/species_defaults")
        if _check_if_species_defaults_set():
            return
        d = get_species_defaults_directory()
        self.assertListEqual([os.path.join(d, "defaults_2010", "tight", "01_H_default"),],
                             get_species_filepaths("defaults_2010/tight", "H"))

    def test_get_num_obfs(self):
        """Test get number of basis functions"""
        testcases = [
            ("valence 3 s 2.", 3),
            ("ion_occ 4 p 5.", 9),
            ("sto 5 4 15", 9),
            ("gaussian 0 3 34.0613410 0.0060252 5.1235746 0.0450211 1.1646626 0.2018973", 3),
            ("gaussian 2 2 5.5510000 0.2000000 1.2350000 1.0000000", 10),
            ("ionic 5 d auto", 5),
            ("hydro 5 f 9.8", 7),
            ("confined 4 f auto", 7),
        ]

        for basis_keystr, n_basis in testcases:
            basis_key, basis_string = basis_keystr.split(maxsplit=1)
            self.assertEqual(get_num_obfs(basis_key, basis_string), n_basis,
                             msg=f"Failed for {basis_key} {basis_string} {n_basis}")

    def test_get_l_nrad(self):
        """Test get angular momentum and number of radial basis functions"""
        testcases = [
            ("valence 3 s 2.", (0, 3)),
            ("ion_occ 4 p 5.", (1, 3)),
            ("sto 5 4 15", (4, 1)),
            ("gaussian 0 3 34.0613410 0.0060252 5.1235746 0.0450211 1.1646626 0.2018973", (0, 3)),
            ("gaussian 2 2 5.5510000 0.2000000 1.2350000 1.0000000", (2, 2)),
            ("ionic 5 d auto", (2, 1)),
            ("hydro 5 f 9.8", (3, 1)),
            ("confined 4 f auto", (3, 1)),
        ]

        for basis_keystr, l_nrad in testcases:
            basis_key, basis_string = basis_keystr.split(maxsplit=1)
            self.assertTupleEqual(get_l_nrad(basis_key, basis_string), l_nrad,
                                  msg=f"Failed for {basis_key} {basis_string} {l_nrad}")


class test_read_species(ut.TestCase):

    def test_read_species(self):
        datadir = pathlib.Path(__file__).parent / "data"
        testcases_json = datadir / "testcases_species.json"
        with testcases_json.open('r') as h:
            verifies = json.load(h)
        for f, verify in verifies.items():
            s = Species.read(datadir / f)

    def test_read_invalid_species(self):
        tf = tempfile.NamedTemporaryFile()

        # Non-existing element
        with open(tf.name, 'w') as h:
            print("species AB", file=h)
        self.assertRaises(ValueError, Species.read, tf.name)

        # Unknown species tag
        with open(tf.name, 'w') as h:
            print("species H", file=h)
            print("unknownkey 123", file=h)
        self.assertRaises(ValueError, Species.read, tf.name)

        # Unknown basis tag
        with open(tf.name, 'w') as h:
            print("species H", file=h)
            print("hydroinvalid", file=h)
        self.assertRaises(ValueError, Species.read, tf.name)
        tf.close()

    def test_read_default(self):
        if not _check_if_species_defaults_set():
            return
        try:
            species_defaults = get_species_defaults_directory()
        except ValueError:
            return
        try:
            s = Species.read_default('H', 'defaults_2010/tight')
        except ValueError:
            pass

    def test_read_multiple(self):
        try:
            pspecies = get_species_filepaths('defaults_2010/tight', 'H')[0]
        except (ValueError, KeyError):
            return
        with open(pspecies, 'r') as h:
            lines = h.readlines()
        tf = tempfile.NamedTemporaryFile()
        with open(tf.name, 'w') as h:
            for _ in range(3):
                for l in lines:
                    print(l, file=h)
        ss = Species.read_multiple(tf.name)
        self.assertEqual(len(ss), 3)
        tf.close()


class test_species_manipulate(ut.TestCase):

    def test_update_basic_tags(self):
        basis = [
            ("valence", "1 s 1.0", False, 0, True),
        ]
        s = Species("H", {}, basis)
        self.assertRaises(KeyError, s.update_basic_tag, "unknown-tag", 111)
        self.assertRaises(KeyError, s.__getitem__, "nucleus")
        s.update_basic_tag("nucleus", 1.008)
        self.assertEqual(s["nucleus"], "1.008")

    def test_export_species(self):
        basis = [
            ("valence", "1 s 1.0", False, 0, True),
            ("gaussian", "0 1 0.1220000", False, 0, True),
            ("gaussian", "2 2 5.5510000 0.2000000 1.2350000 1.0000000", False, 0, True),
        ]
        s = Species("H", {}, basis)
        s.export()

    def test_get_adjust_cut_pot(self):
        basis = [
            ("valence", "1 s 1.0", False, 0, True),
        ]
        s = Species("H", {}, basis)
        # Do nothing
        s.adjust_cut_pot()
        # Raise when cut_pot has been set
        self.assertRaises(KeyError, s.get_cut_pot)
        # Raise when incomplete cut_pot is parsed and cut_pot has not been set yet
        self.assertRaises(ValueError, s.adjust_cut_pot, onset=4.0, width=None, scale=None)
        # Raise when getting an invalid cut_pot
        s.update_basic_tag("cut_pot", "4.0 2.0")
        self.assertRaises(ValueError, s.get_cut_pot)
        s.adjust_cut_pot(onset=4.0, width=2.0, scale=1.0)

    def test_get_basis(self):
        basis_raw = [
            ["valence", "1 s 1.0", False, 0, True],
            ["hydro", "2 s 1.0", False, 1, False],
            ["hydro", "3 s 1.0", False, 2, False],
            ["hydro", "4 s 1.0", True, -1, False],
            ["hydro", "2 p 1.0", True, -1, False],
        ]
        s = Species("H", {}, basis_raw)
        self.assertEqual(len(s.get_basis()), 5)
        self.assertEqual(len(s.get_basis("valence")), 1)
        self.assertEqual(len(s.get_basis("hydro")), 4)
        self.assertEqual(len(s.get_basis(is_aux=True)), 2)
        self.assertEqual(len(s.get_abf()), 2)
        self.assertEqual(len(s.get_basis(enabled=False)), 4)

    def test_switch_tier(self):
        basis_raw = [
            ["valence", "1 s 1.0", False, 0, True],
            ["hydro", "2 s 1.0", False, 1, False],
            ["hydro", "3 s 1.0", False, 2, False],
            ["hydro", "4 s 1.0", True, -1, False],
            ["hydro", "2 p 1.0", True, -1, False],
        ]
        s = Species("H", {}, basis_raw)
        self.assertEqual(len(s.get_basis(enabled=False)), 4)
        s.switch_tier(-1, True, True)
        self.assertEqual(len(s.get_basis(enabled=False)), 2)
        s.switch_tier(0, False, False)
        self.assertEqual(len(s.get_basis(enabled=False)), 3)


if __name__ == '__main__':
    ut.main()
