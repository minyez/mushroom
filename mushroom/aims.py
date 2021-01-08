# -*- coding: utf-8 -*-
"""FHI-aims related"""
from typing import Tuple, List
import numpy as np

from mushroom.core.typehint import RealVec3D
from mushroom.core.bs import BandStructure

def decode_band_output_line(bstr: str) -> Tuple[List, List, List]:
    """decode a line of band output file, e.g. scfband1001.out, band2001.out

    Each line is like

        index k1 k2 k3 occ_1 ene_1 occ_2 ene_2 ...

    Args:
        bstr (str)

    Returns:
        three list: k-points, occupation numbers, energies
    """
    values = bstr.split()
    try:
        kpts = list(map(float, values[1:4]))
        occ = list(map(float, values[4::2]))
        ene = list(map(float, values[5::2]))
        return kpts, occ, ene
    except IndexError as err:
        raise ValueError("bad input string for aims band energy: {}".format(bstr)) from err

def read_band_output(bfile, *bfiles, unit: str='ev') -> Tuple[BandStructure, List[RealVec3D]]:
    """read band output files and return a Band structure

    Note that all band energies are treated in the same spin channel,
    the resulting ``BandStructure`` object always has nspins=1

    Args:
        bfile (str)
        unit (str): unit of energies, default to ev

    Returns:
        BandStructure, k-points
    """
    bfiles = (bfile, *bfiles)
    kpts = []
    occ = []
    ene = []
    for bf in bfiles:
        data = np.loadtxt(bf, unpack=True)
        kpts.extend(np.column_stack([data[1], data[2], data[3]]))
        occ.extend(np.transpose(data[4::2]))
        ene.extend(np.transpose(data[5::2]))
    kpts = np.array(kpts)
    occ = np.array([occ,])
    ene = np.array([ene,])
    return BandStructure(ene, occ, unit=unit), kpts

