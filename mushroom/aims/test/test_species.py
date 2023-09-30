#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import unittest as ut
import pathlib
import os
import json


from mushroom.aims.species import _SPECIES_DEFAULTS_ENV, \
    search_basis_directories, get_species_defaults_directory, get_basis_directory_from_alias, \
    get_specie_filename


def _skip_when_species_defaults_not_set():
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


class test_species(ut.TestCase):

    def test_species_diretories(self):
        # test can be done without an existing aims directory
        self.assertRaises(ValueError, search_basis_directories, "some/random/path/should/not/exist")
        self.assertListEqual([], search_basis_directories("some/random/path/should/not/exist", False))
        if _skip_when_species_defaults_not_set():
            return
        get_species_defaults_directory()
        paths = search_basis_directories()
        self.assertIn("defaults_2010/tight", paths)
        print(paths)

    def test_alias(self):
        self.assertEqual(get_basis_directory_from_alias("tight"), "defaults_2020/tight")

    def test_get_specie_filename(self):
        self.assertRaises(ValueError, get_specie_filename, "Ne", "unknown", "path/to/species_defaults")
        if _skip_when_species_defaults_not_set():
            return
        d = get_species_defaults_directory()
        self.assertEqual(os.path.join(d, "defaults_2010", "tight", "01_H_default"),
                         get_specie_filename("H", "defaults_2010/tight"))


if __name__ == '__main__':
    ut.main()
