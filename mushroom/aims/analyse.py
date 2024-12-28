# -*- coding: utf-8 -*-
"""convenient functions to analyse FHI-aims input/output"""
import os
import re
import pathlib
from typing import Union
import numpy as np

from mushroom.core.logger import loggers
from mushroom.aims.stdout import StdOut


__all__ = [
    "get_dimensions",
    "get_chemical_potential",
    "is_finished_aimsdir",
    "get_atoms_from_geometry",
    "get_recp_latt_from_geometry",
]

_logger = loggers["aims"]


def get_dimensions(aimsout):
    """display dimensions in the FHI-aims calculation from aimsout

    Args:
        aimsout: aims stdout file

    Returns:
        str, format string for the key-value pair
        dict, entry of dimension and its value
    """
    s = StdOut(aimsout)
    dict_str_dim = {
        "Spins": s._nspins,
        "K-points": s._nkpts,
        "States/bands": s._nbands,
        "OBS (orbital basis set)": s._nbasis,
        "ABF (auxiliary basis function)": s._nbasbas,
        "Radial functions": s._nrad,
        "Basis in H Integrals": s._nbasis_H,
        "Basis in UC": s._nbasis_uc,
        "Electrons": s._nelect,
        "DFT SCF iterations": s._nscf_ite,
        "Super-cells": s._n_cells,
        "Super-cells (packed)": s._n_cells_pm,
        "Non-zero elements of all H(R)": s._n_matrix_size_H,
        "Real-space grid points": s._n_full_points,
        "Real-space grid points (non-zero)": s._n_full_points_nz,
    }
    lstr = max([len(x) for x in dict_str_dim.keys()])
    format_str = "# %-{}s : %s".format(lstr)
    return format_str, dict_str_dim


def get_chemical_potential(aimsout):
    """Get chemical potential

    Args:
        aimsout (str): aims output file

    Returns:
        float, last chemical potential printed in FHIaims output, in eV

    Caveat:
        not tested for nspins=2
    """
    chempot = None
    with open(aimsout, 'r') as h:
        for l in h.readlines():
            if l.startswith("  | Chemical Potential"):
                chempot = float(l.split()[-2])
    return chempot


def is_finished_aimsdir(dirpath: Union[str, os.PathLike], aimsout_pat: str = "aims.out*",
                        use_regex: bool = False) -> str:
    """check if the calculation inside dirpath is completed.

    This is done by searching aims output files matching pattern ``aimsout_pat``
    and checking if they are finished.

    Args:
        dirpath (str and PathLike): the directory containing aims input and output (if exists)
        aimsout_pat (str): wildcard pattern to match the aims output file.
        use_regex (bool): if True, `aimsout_pat` will be treated as regular expression to
            match the file name pattern instead of wildcard.

    Returns:
        str, path of finished aims stdout, or None if there is no finished calculation
    """
    if use_regex:
        pattern = re.compile(aimsout_pat)
        for f in os.listdir(dirpath):
            if os.path.isdir(f):
                continue
            matched = pattern.match(f)
            if matched is not None:
                aimsout = os.path.join(dirpath, f)
                stdout = StdOut(aimsout, lazy_load=True)
                if stdout.is_finished():
                    return aimsout
    else:
        for aimsout in pathlib.Path(dirpath).glob(aimsout_pat):
            # use lazy load to check only the last finishing line
            stdout = StdOut(aimsout, lazy_load=True)
            if stdout.is_finished():
                return aimsout.name
    return None


def get_atoms_from_geometry(path_geometry: str = "geometry.in"):
    """Get the atoms in the geometry file

    Args:
        path_geometry (str)

    Returns:
        List of str
    """
    with open(path_geometry, 'r') as h:
        lines = h.readlines()
    atms = []
    for l in lines:
        if l.strip().startswith("atom"):
            atms.append(l.split()[-1])
    return atms


def get_recp_latt_from_geometry(path_geometry: str = "geometry.in"):
    """get reciprocal lattice vectors of from aims geometry file"""
    latt = []
    with open(path_geometry, 'r') as h:
        lines = h.readlines()
        for l in lines:
            if l.strip().startswith("lattice_vector"):
                latt.append(list(map(float, l.split()[1:4])))
    if len(latt) != 3:
        raise ValueError("Lattice vectors less than 1, check your geometry file!")
    latt = np.array(latt)
    return np.cross(latt[(1, 2, 0), :], latt[(2, 0, 1), :]) / np.linalg.det(latt) * 2.0E0 * np.pi
