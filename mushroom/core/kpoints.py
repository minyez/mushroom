#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""utilities related to k-mesh"""
from itertools import product
from collections.abc import Iterable
import numpy as np
try:
    import spglib
except ImportError:
    spglib = None

from mushroom.core.logger import create_logger
from mushroom.core.ioutils import raise_no_module

__all__ = [
        "KPath",
        "MPGrid",
        ]

_logger = create_logger("kpoints")
del create_logger

class KPath:
    """object to manipulate path in reciprocal k space

    Special kpoints are recognized automatically.

    Args:
        kpts (list): the coordinates of k points
        recp_latt (3x3 array): the reciprocal lattice vectors, [b1, b2, b3].
            If parsed, it will be used to convert the kpts to Cartisian coordiantes.
    """

    def __init__(self, kpts, recp_latt=None, unify_x: bool=False):
        self._nkpts = len(kpts)
        if np.shape(kpts) != (self._nkpts, 3):
            raise ValueError("bad shape of parsed kpoints")
        self.kpts = np.array(kpts)
        if recp_latt is not None:
            self.kpts = np.matmul(kpts, recp_latt)
        self._ksegs = None
        self._find_ksegs()
        self._unify_x = unify_x
        self._x = None
        self._special_x = None
        self._index_special_x = None

    def _find_ksegs(self):
        self._ksegs = find_k_segments(self.kpts)

    def _compute_x(self):
        """calculate 1d abscissa of kpoints"""
        xs = []
        ispks = []
        accumu_l = 0.0
        for i, (st, ed) in enumerate(self._ksegs):
            l = np.linalg.norm(self.kpts[st, :] - self.kpts[ed, :])
            # remove duplicate
            if not st in ispks and not st-1 in ispks:
                ispks.append(st)
            ispks.append(ed)
            # skip the starting point if it is the same as the endpoint of last segment
            skip = 0
            if i > 0:
                if st == self._ksegs[i-1][1]:
                    skip = 1
            x = accumu_l + np.linalg.norm(self.kpts[st:ed+1, :] - self.kpts[st, :], axis=1)[skip:]
            xs.extend(x)
            accumu_l += l
        self._x = np.array(xs)
        if self._unify_x:
            self._x /= self._x[-1]
        self._special_x = self._x[ispks]
        self._index_special_x = np.array(ispks)

    @property
    def x(self):
        """1d abscissa of points on kpath"""
        if self._x is None:
            self._compute_x()
        return self._x

    @property
    def special_x(self):
        """1d abscissa of points on kpath"""
        if self._special_x is None:
            self._compute_x()
        return self._special_x


class MPGrid:
    """Monkhorst-Pack kpoint mesh

    If shift is not parsed, the grids always have Gamma in it.

    Args:
        nk1, nk2, nk3 (int)
        spgcell (tuple): lattice vectors, internal positions, atom indices
        shift (ndarry)
        sort (bool)
    """
    _dtype = 'float64'

    def __init__(self, nk1: int, nk2: int, nk3: int, spgcell=None,
                 shift=None, sort: bool = False):
        self._kdivs = np.array([nk1, nk2, nk3])
        if shift is None:
            self._shift = np.zeros(3)
        else:
            self._shift = np.array(shift, dtype=self._dtype)
        self._require_sort = sort
        self._spgcell = spgcell

    @property
    def kdivs(self):
        """division along three reciprocal vectors"""
        return self._kdivs

    @property
    def grids(self):
        """array, integer grids of kmesh
        """
        return uniform_int_kmesh(self._kdivs[0], self._kdivs[1], self._kdivs[2],
                                 shift=self._shift, sort=self._require_sort)

    @property
    def kpts(self):
        """array, reciprocal coordinates of mesh points
        """
        return np.divide(self.grids, self._kdivs)

    @property
    def nkpts(self):
        """int, number of mesh points"""
        return len(self.kpts)

    def get_ir_grids(self):
        """get the irreducible grid points"""
        if self._spgcell is None:
            raise ValueError("need cell to compute irreducible kpoints")
        raise_no_module(spglib, "Spglib")
        mapping, grids = spglib.get_ir_reciprocal_mesh(self._kdivs, self._spgcell,
                                                       is_shift=self._shift)
        return np.divide(grids, self._kdivs), mapping


def find_k_segments(kpts):
    """find line segments of parsed kpoint path

    Usually, the number of kpoints on one line segments is no less than 3.

    Args:
        kvec (array-like): the kpoint vectors to analysis, shape, (n,3)

    Returns:
        list, with tuple as members. Each tuple has 2 int members,
        the indices of kpoint vectors at the beginning and end of
        a line segment
    """
    ksegs = []
    nkpts = len(kpts)
    # the change in vector between two kpoints
    # dtype required
    kpts = np.array(kpts, dtype='float64')
    deltak = kpts[1:, :] - kpts[:-1, :]
    l = np.linalg.norm(deltak, axis=1)
    for i in range(nkpts-1):
        if np.isclose(l[i], 0):
            deltak[i, :] = 0.
        else:
            deltak[i, :] = deltak[i, :] / l[i]
    dotprod = np.sum(deltak[1:, :] * deltak[:-1, :], axis=1)
    st = 0
    ed = 2
    while ed < nkpts:
        # a new segment when direction of delta vector changes
        # i.e. dot product is not 1 any more
        if not np.isclose(dotprod[ed-2], 1.):
            ksegs.append((st, ed-1))
            st = ed - 1
            # introduce a gap if the adjacent points are the same,
            # or the next segment starts from a new point
            if np.allclose(deltak[ed-1,:], 0.) or \
                    (ed < nkpts - 1 and not np.isclose(dotprod[ed-1], 1.)):
                st += 1
                ed += 1
        ed += 1
    if ed - st >= 2:
        ksegs.append((st, ed-1))
    return ksegs


def uniform_int_kmesh(nk1: int, nk2: int, nk3: int,
                      shift: Iterable, sort=False):
    """generate a uniform or homogeneous kpoint mesh

    Args:
        nk1, nk2, nk3 (int): the number of division on each reciprocal vector
        shift (Iterable): containing 3 integers

    Returns:
        ndarray
    """
    divisions = np.array([nk1, nk2, nk3])
    ikmesh = [[ik1, ik2, ik3] for ik1, ik2, ik3 in product(*map(range, divisions))]
    ikmesh = np.array(ikmesh)
    centering = (divisions - 1) // 2
    ikmesh = ikmesh - centering
    if sort:
        indices = list(range(nk1*nk2*nk3))
        norm = np.linalg.norm(ikmesh, axis=1)
        indices.sort(key=norm.__getitem__)
        ikmesh = ikmesh[indices]
    try:
        return ikmesh + 0.5 * np.array(shift)
    except ValueError as err:
        raise ValueError("expected Iterable for shift, got %s" % type(shift)) from err

