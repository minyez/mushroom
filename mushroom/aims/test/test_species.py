#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import unittest as ut
import pathlib
import os
import json


from mushroom.aims.species import _SPECIES_DEFAULTS_ENV, search_basis_directories, get_species_defaults_directory


class test_species(ut.TestCase):

    def test_species_diretories(self):
        try:
            species_defaults = os.environ[_SPECIES_DEFAULTS_ENV]
        except KeyError:
            try:
                from mushroom.__config__ import aims_species_defaults as species_defaults
            except ImportError:
                print("Environment variable {} not set, skip species directory test".format(_SPECIES_DEFAULTS_ENV))
                return
        get_species_defaults_directory()
        self.assertRaises(ValueError, search_basis_directories, "some/random/path/should/not/exist")
        paths = search_basis_directories()
        self.assertIn("defaults_2010/tight", paths)
        print(paths)


if __name__ == '__main__':
    ut.main()
