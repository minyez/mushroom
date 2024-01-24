# -*- coding: utf-8 -*-
"""Utitlies for handling aims input/output.

Functions here are used for simple tasks.
For more comprehensive usage, please use classes and functions in other modules
"""

import os
from typing import Union

import numpy as np


def get_lattice_vectors(path_geometry: Union[str, os.PathLike] = "geometry.in"):
    """get lattice vectors from geometry file"""
    latt = []
    with open(path_geometry, 'r') as h:
        lines = h.readlines()
        for l in lines:
            if l.strip().startswith("lattice_vector"):
                latt.append(list(map(float, l.split()[1:4])))
    return np.array(latt)
