# -*- coding: utf-8 -*-
"""convenient functions to analyse FHI-aims input/output"""
import pathlib

from mushroom.aims.stdout import StdOut


def display_dimensions(aimsout):
    """display dimensions in the FHI-aims calculation from aimsout"""
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
    for sd in dict_str_dim.items():
        if sd[1] is not None:
            print(format_str % sd)
        else:
            print(format_str % (sd[0], "(NOT FOUND)"))


def is_finished_aimsdir(dirpath: Path, aimsout_pat: str = "aims.out*") -> str:
    """check if the calculation inside dirpath is completed.

    This is done by searching aims output files matching pattern ``aimsout_pat``
    and checking if they are finished.

    Args:
        dirpath (str and PathLike): the directory containing aims input and output (if exists)
        aimsout_pat (str): wildcard pattern to match the aims output file.

    Returns:
        str, path of finished aims stdout, or None if there is no finished calculation
    """
    dirpath = pathlib.Path(dirpath)
    for aimsout in dirpath.glob(aimsout_pat):
        stdout = StdOut(aimsout)
        if stdout.is_finished():
            return aimsout.name
    return None
