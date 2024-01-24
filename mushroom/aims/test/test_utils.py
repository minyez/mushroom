#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import unittest as ut
import pathlib
import tempfile

import numpy as np

from mushroom.aims.utils import get_lattice_vectors


class test_geometry_related_utils(ut.TestCase):

    def test_get_lattice_vectors(self):
        tf = tempfile.NamedTemporaryFile()
        with open(tf.name, 'w') as h:
            print("lattice_vector 1.0 0.0 1.0", file=h)
            print("lattice_vector 1.0 2.0 0.5", file=h)
            print("lattice_vector 3.0 4.0 2.5", file=h)
        latt_ref = [[1.0, 0.0, 1.0], [1.0, 2.0, 0.5], [3.0, 4.0, 2.5]]
        latt_ref = np.array(latt_ref)
        latt = get_lattice_vectors(tf.name)
        self.assertTrue(np.allclose(latt_ref, latt))


if __name__ == "__main__":
    ut.main()
