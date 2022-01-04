# -*- coding: utf-8 -*-
"""Utilities for processing crystall-related quantities"""
from copy import deepcopy
from typing import List, Iterable, Tuple
import numpy as np
from numpy import cos, sin
from mushroom.core.typehint import Latt3T3
from mushroom.core.constants import PI
from mushroom.core.logger import create_logger

_logger = create_logger("cryutil")
del create_logger

def get_recp_latt(latt: Latt3T3):
    """get the reciprocal lattice vectors from the real vectors"""
    return np.cross(latt[(1, 2, 0), :], latt[(2, 0, 1), :]) / np.linalg.det(latt) * 2.0E0 * PI

def get_latt_vecs_from_latt_consts(a: float, b: float, c: float,
                                   alpha: float = 90.,
                                   beta: float = 90.,
                                   gamma: float = 90.,
                                   decimals: int = 6) -> Latt3T3:
    """Convert lattice constants to lattice vectors in right-hand system

    Note that by now a1 is forced along x axis, and (a1,a2) is forced on the xOy plane, i.e.
        a1_y = a1_z = a2_z = 0

    Args:
        a, b, c (float): length of lattice vectors (>0)
        alpha, beta, gamma (float): angles between lattice vectors in degree.
            90. is used for each as default.
        decmials (int): round the calculated vectors, parsed to numpy ``around`` function
    """
    angle_thres = 1.E-3
    a = abs(a)
    b = abs(b)
    c = abs(c)
    is_ortho = all(map(lambda x: abs(x-90.) <= angle_thres, [alpha, beta, gamma]))
    if is_ortho:
        return [[a, 0., 0.], [0., b, 0.], [0., 0., c]]
    alpha *= PI / 180.
    beta *= PI / 180.
    gamma *= PI / 180.
    ca, cb, cg = cos([alpha, beta, gamma])
    sa, sb, sg = sin([alpha, beta, gamma])
    a1 = [a, 0., 0.]
    a2 = [b*cg, b*sg, 0.0]
    a3 = [c*cb, c/sg*(ca-cg*cb),
          c/sg*np.sqrt(sb**2*sg**2 - ca**2 - cg**2*cb**2 + 2.0*ca*cb*cg)
          ]
    return np.round([a1, a2, a3], decimals=decimals)


def get_latt_consts_from_latt_vecs(latt) -> Tuple[float]:
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


def get_all_atoms_from_symops(atms_ineq: Iterable[str], posi_ineq, symops: dict,
                              left_mult: bool = True, latt: Latt3T3 = np.diag((1., 1., 1.)),
                              unit: str = "ang", iden_thres: float = 1e-5):
    """Get atomic symbols and positions of all atoms in the cell
    by performing symmetry operations on inequivalent atoms

    Args:
        atms_ineq (list of str):
        posi_ineq (array-like): positions in direct coordinate
        symops (dict): dictionary containing symmetry operations
        left_mult (bool):
            True : x' = Rx + t
            False: x'^T = x^T R + t^T
        latt (ndarray, (3,3)): lattice vectors
        unit (str): length unit
        iden_thres (float) : threshold in unit for equalize two atoms
    """
    if len(atms_ineq) != len(posi_ineq):
        raise ValueError("inequivalent atoms and positions are inconsistent")
    if not isinstance(symops, dict):
        raise ValueError("symops must be a dictionary")

    posi = []
    xyzs = []
    atms = []
    _logger.debug("atms_ineq: %r", atms_ineq)
    _logger.debug("posi_ineq: %r", posi_ineq)
    try:
        _logger.debug("# of symops: %r", len(symops["translations"]))
        rots, trans = symops["rotations"], symops["translations"]
    except KeyError:
        raise KeyError("symops must contain keys `rotations` and `translations`")
    for r, t in zip(rots, trans):
        if not left_mult:
            r = np.transpose(r)
        for i, p in enumerate(posi_ineq):
            a = np.add(np.dot(r, p), t)
            # move to the lattice at origin
            a = np.subtract(a, np.floor(a))
            xyz = np.dot(latt, a)
            try:
                for old_xyz in xyzs:
                    if np.allclose(xyz, old_xyz, atol=iden_thres):
                        raise ValueError
            except ValueError:
                _logger.debug("Found duplicate: %r", a)
                continue
            else:
                _logger.debug("Add new atom: %r", a)
                atms.append(atms_ineq[i])
                posi.append(a)
                xyzs.append(xyz)
    return atms, posi

# pylint: disable=C0301
def periodic_duplicates_in_cell(direct_coord):
    '''Return the coordinates and numbers of the duplicates of an atom
    in a cell due to lattice translation symmetry

    Args:
        direct_coord (array): the direct coordinate of an atom in the cell

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
    _pos = np.array(direct_coord, dtype="float64")
    assert np.shape(_pos) == (3,)
    assert all(_pos - 1.0 < 0)
    _dupcs = []
    _dupcs.append(direct_coord)
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


def atms_from_sym_nat(sym: Iterable[str], nat: Iterable[int]) -> List[str]:
    """Generate ``atom`` list for ``Cell`` initilization from list of atomic symbols
    and number of atoms

    Args :
        sym (list of str) : atomic symbols
        nat (list of int) : number of atoms for each symbol

    Returns :
        a list of str, containing symbol of each atom in the cell

    Examples:
    >>> atms_from_sym_nat(["C", "Al", "F"], [2, 3, 1])
    ["C", "C", "Al", "Al", "Al", "F"]
    """
    if len(sym) != len(nat):
        raise ValueError("Inconsistent symbols and numbers: {}, {}".format(sym, nat))
    atms = []
    for s, n in zip(sym, nat):
        for _ in range(n):
            atms.append(s)
    return atms


def sym_nat_from_atms(atms: Iterable[str]):
    """Generate lists of atomic symbols and number of atoms from whole atoms list

    The order of appearence of the element is conserved in the output.

    Args :
        atms (list of str) : symbols of each atom in the cell

    Returns :
        list of str : atomic symbols
        list of int : number of atoms for each symbol

    Examples:
    >>> sym_nat_from_atms(["C", "Al", "Al", "C", "Al", "F"])
    ["C", "Al", "F"], [2, 3, 1]
    """
    syms = []
    nat_dict = {}
    for at in atms:
        if at in syms:
            nat_dict[at] += 1
        else:
            syms.append(at)
            nat_dict.update({at: 1})
    return syms, [nat_dict[at] for at in syms]


def select_dyn_flag_from_axis(axis, relax: bool = False) -> List[bool]:
    """Generate selective dynamic flags, i.e. [bool, bool, bool]

    Args:
        relax (bool): if True, the flag for axis will be set as True.
            Otherwise False
    """
    flag = [not relax, not relax, not relax]
    alist = axis_list(axis)
    for a in alist:
        flag[a-1] = not flag[a-1]
    return flag

def brav_from_latt_consts(a: float, b: float, c: float,
                          alpha: float, beta: float, gamma: float,
                          decimals: int = 6):
    """determine the type of Bravais lattice from the lattice constants

    Returns:
        string, tuple. string
    """
    raise NotImplementedError

def axis_list(axis) -> tuple:
    """Generate axis indices from ``axis``

    Args:
        axis (int or list of int)

    Returns:
        tuple
    """
    _aList = []
    if isinstance(axis, int):
        if axis == 0:
            _aList = [1, 2, 3]
        if axis in range(1, 4):
            _aList = [axis]
    elif isinstance(axis, (list, tuple)):
        _aSet = list(set(axis))
        for _a in _aSet:
            try:
                assert isinstance(_a, int)
            except AssertionError:
                pass
            else:
                if _a == 0:
                    _aList = [1, 2, 3]
                    break
                if _a in range(1, 4):
                    _aList.append(_a)
    return tuple(_aList)

