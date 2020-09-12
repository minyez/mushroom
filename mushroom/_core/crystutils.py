# -*- coding: utf-8 -*-
"""Utilities for processing crystall-related quantities"""
import numpy as np
from mushroom._core.constants import PI

def get_latt_vecs_from_latt_consts(a, b, c, alpha=90, beta=90, gamma=90):
    """Convert lattice constants to lattice vectors in right-hand system

    Currently support orthormrhobic lattice only!!!

    Args:
        a, b, c (float): length of lattice vectors
        alpha, beta, gamma (float): angles between lattice vectors in degree.
            90 used as default.
    """
    a = abs(a)
    b = abs(b)
    c = abs(c)
    if alpha != 90 or beta != 90 or gamma != 90:
        raise NotImplementedError
    return [[a, 0, 0], [0, b, 0], [0, 0, c]]


def get_latt_consts_from_latt_vecs(latt):
    """Convert lattice vectors in right-hand system to lattice constants

    Args:
        latt (2d-array): lattice vectors, shape (3,3)
    
    Returns:
        6 floats, a, b, c, alpha, beta, gamma (in degree)
    """
    try:
        assert np.shape(latt) == (3, 3)
    except AssertionError:
        raise ValueError("Invalid lattice vectors")
    a = np.array(latt)
    alen = np.linalg.norm(a, axis=1)
    angle = []
    for i in range(3):
        j = (i + 1) % 3
        k = (i + 2) % 3
        _cos = np.dot(a[j, :], a[k, :]) / alen[j] / alen[k]
        angle.append(np.arccos(_cos))
    # convert to degree
    angle = np.array(angle, dtype="float64") / PI * 180.0
    return (*alen, *angle)


def get_all_atoms_from_sym_ops(ineq_atms, ineq_posi, symops, left_mult=True):
    """Get atomic symbols and positions of all atoms in the cell
    by performing symmetry operations on inequivalent atoms

    Args:
        inEqAtoms (list of str):
        inEqPos (array-like):
        symops (dict): dictionary containing symmetry operations
        left_mult (bool)
            True : x' = Rx + t
            False: x'^T = x^T R + t^T
    """
    assert len(ineq_atms) == len(ineq_posi)
    assert isinstance(symops, dict)
    posi = []
    atms = []
    for r, t in zip(symops["rotations"], symops["translations"]):
        if not left_mult:
            r = np.transpose(r)
        for i, p in enumerate(ineq_posi):
            a = np.add(np.dot(r, p), t)
            # move to the lattice at origin
            a = np.subtract(a, np.floor(a))
            try:
                for xyz in posi:
                    if np.allclose(xyz, a):
                        raise ValueError
            except ValueError:
                continue
            else:
                atms.append(ineq_atms[i])
                posi.append(a)
    return atms, posi


def periodic_duplicates_in_cell(directCoord):
    '''Return the coordinates and numbers of the duplicates of an atom
    in a cell due to lattice translation symmetry

    Args:
        directCoord (array): the direct coordinate of an atom in the cell

    Note:
        The function works only when each component belongs to [0,1)

    TODO:
        Generalize this function to mirrors in n-th lattice shell

    Returns:
        tuple : the coordinates of all the atom duplicates due to transilational symmetry
        int : the number of duplicates

    Examples:
    >>> periodic_duplicates_in_cell([0,0,0])
    (([0, 0, 0], [1.0, 0, 0], [0, 1.0, 0], [1.0, 1.0, 0], [0, 0, 1.0], [1.0, 0, 1.0], [0, 1.0, 1.0], [1.0, 1.0, 1.0]), 8)
    >>> periodic_duplicates_in_cell([0,0.4,0])
    (([0, 0.4, 0], [1.0, 0.4, 0], [0, 0.4, 1.0], [1.0, 0.4, 1.0]), 4)
    '''
    from copy import deepcopy
    _pos = np.array(directCoord, dtype="float64")
    assert np.shape(_pos) == (3,)
    assert all(_pos - 1.0 < 0)
    _dupcs = []
    _dupcs.append(directCoord)
    # non-zero component
    _n = 2 ** (3 - np.count_nonzero(_pos))
    _iszero = _pos == 0
    for i in range(3):
        if _iszero[i]:
            _trans = deepcopy(_dupcs)
            for _c in _trans:
                _c[i] = 1.0
            _dupcs.extend(_trans)
    return tuple(_dupcs), _n
