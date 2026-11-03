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

from mushroom.core.logger import loggers
from mushroom.core.utils import raise_no_module

__all__ = [
    "KPathLinearizer", "format_ksymbols", "split_kpath_breaks",
    "MPGrid",
]

_logger = loggers["kpoints"]


def check_on_line_segment(x_0, x_st, x_ed, atol=1e-5):
    """Check if point x_0 lies on the line segment specified by points x_st and x_ed

    Args:
        x_st: start of the line segment
        x_ed: end of the line segment
        x_0: point to test
        atol: absolute coordinate tolerance for the segment check
        x_0, x_st, x_ed (1d-array-like)

    Returns:
        True if x_0 lies between x_st and x_ed, otherwise False
    """
    x0st = np.subtract(x_0, x_st)
    x0ed = np.subtract(x_0, x_ed)
    dot = np.dot(x0st, x0ed)  # to check if dot is between the two points
    distance = np.linalg.norm(np.cross(x0st, x0ed)) / np.linalg.norm(np.subtract(x_ed, x_st))
    return np.isclose(distance, 0.0, atol=atol) and dot <= 0.0


class KPathLinearizer:
    """Manipulate a reciprocal-space path and identify its straight segments.

    Args:
        kpts (array-like): Fractional k-point coordinates, shape (nkpts, 3).
        recp_latt (array-like or None): Reciprocal vectors as rows, shape (3, 3).
            If supplied, coordinates are converted to Cartesian form in these
            vectors' units. For effective masses use inverse Angstrom including 2pi.
        unify_x (bool): Normalize the plotting abscissa to end at one. Physical
            coordinates returned by kpts are unaffected.
        ksymbols (sequence of str or None): Plain special-point labels in path
            order, stored as an immutable tuple and exposed as a read-only property.

    Raises:
        ValueError: If kpts does not have shape (nkpts, 3).
    """

    def __init__(self, kpts, recp_latt=None, unify_x: bool = False, ksymbols=None):
        self._ksymbols = None if ksymbols is None else tuple(ksymbols)
        self._use_cartesian = False
        self._recp_latt = None
        self._nkpts = len(kpts)
        if np.shape(kpts) != (self._nkpts, 3):
            raise ValueError("bad shape of parsed kpoints")
        self._kpts = np.array(kpts)
        if recp_latt is not None:
            self._kpts = np.matmul(kpts, recp_latt)
            self._recp_latt = recp_latt
            self._use_cartesian = True
        self._ksegs = None
        self._unify_x = unify_x
        self._x = None
        self._special_x = None
        self._index_special_x = None
        self._xmax_non_unifty = None
        self._find_ksegs()
        _logger.debug("Found segments: %r", self._ksegs)

    @property
    def ksymbols(self):
        """Plain special-point labels as a tuple, or None."""
        return self._ksymbols

    @property
    def is_cartesian(self):
        """Whether coordinates were converted with a reciprocal lattice."""
        return self._use_cartesian

    @property
    def segments(self):
        """Inclusive start/end index pairs as an immutable tuple."""
        return tuple(tuple(segment) for segment in self._ksegs)

    @property
    def kpts(self):
        """Copy of (nkpts, 3) coordinates, Cartesian when is_cartesian is true."""
        return self._kpts.copy()

    @property
    def nkpts(self):
        """Number of points along the path."""
        return self._nkpts

    def _find_ksegs(self):
        self._ksegs = find_k_segments(self._kpts)

    def _compute_x(self):
        """calculate 1d abscissa of kpoints"""
        xs = []
        ispks = []
        accumu_l = 0.0
        for i, (st, ed) in enumerate(self._ksegs):
            l = np.linalg.norm(self._kpts[st, :] - self._kpts[ed, :])
            # remove duplicate
            if st not in ispks and st - 1 not in ispks:
                ispks.append(st)
            ispks.append(ed)
            # skip the starting point if it is the same as the endpoint of last segment
            skip = 0
            if i > 0:
                if st == self._ksegs[i - 1][1]:
                    skip = 1
            x = accumu_l + np.linalg.norm(
                self._kpts[st:ed + 1, :] - self._kpts[st, :], axis=1)[skip:]
            xs.extend(x)
            accumu_l += l
        self._x = np.array(xs)
        self._xmax_non_unifty = self._x[-1]
        if self._unify_x:
            self._x /= self._x[-1]
        self._special_x = self._x[ispks]
        self._index_special_x = np.array(ispks)
        _logger.debug("Special coordinates in 1D: %r", self._special_x)

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

    @property
    def X(self):
        """alias to special_x"""
        return self.special_x

    def locate(self, kpts):
        """Locate the 1d coordinates of k-points on the path

        Args:
            kpts (2d-array, shape N*3): k-points in fractional coordinates

        Returns:
            a list of float lists or None
        """
        if self._x is None:
            self._compute_x()
        xs_all = []
        if len(kpts) == 0:
            return xs_all
        if self._use_cartesian:
            kpts = np.matmul(kpts, self._recp_latt)
        kpts = np.array(kpts)
        for k in kpts:
            xs = None
            for (st, ed) in self._ksegs:
                if check_on_line_segment(k, self._kpts[st], self._kpts[ed]):
                    x = np.linalg.norm(k - self._kpts[st])
                    if self._unify_x:
                        # print(x, self._xmax_non_unifty)
                        x /= self._xmax_non_unifty
                    if xs is None:
                        xs = []
                    xs.append(x + self.x[st])
            xs_all.append(xs)
        return xs_all


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
        """array, integer grids of kmesh"""
        return uniform_int_kmesh(self._kdivs[0], self._kdivs[1], self._kdivs[2],
                                 shift=self._shift, sort=self._require_sort)

    @property
    def kpts(self):
        """array, reciprocal coordinates of mesh points"""
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
        kpts (array-like): the kpoint vectors to analysis, shape, (n,3)

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
    for i in range(nkpts - 1):
        if np.isclose(l[i], 0):
            deltak[i, :] = 0.
        else:
            deltak[i, :] = deltak[i, :] / l[i]
    # print(deltak)
    # dotprod[i] = (kpt[i+2] - kpt[i+1]) . (kpt[i+1] - kpt[i])
    dotprod = np.sum(deltak[1:, :] * deltak[:-1, :], axis=1)
    st = 0
    ed = 2
    while ed < nkpts:
        # a new segment when direction of delta vector changes
        # i.e. dot product is not 1 any more
        if not np.isclose(dotprod[ed - 2], 1.):
            ksegs.append((st, ed - 1))
            st = ed - 1
            # introduce a gap if the adjacent points are the same,
            # or the next segment starts from a new point
            if np.allclose(deltak[ed - 1, :], 0.) or \
                    (ed < nkpts - 1 and not np.isclose(dotprod[ed - 1], 1.)):
                st += 1
                ed += 1
        ed += 1
    if ed - st >= 2:
        ksegs.append((st, ed - 1))
    return ksegs


def uniform_int_kmesh(nk1: int, nk2: int, nk3: int,
                      shift: Iterable, sort=False):
    """generate a uniform or homogeneous kpoint mesh

    Args:
        sort: sort the returned vectors using the requested convention
        nk3: number of mesh points along the third reciprocal vector
        nk2: number of mesh points along the second reciprocal vector
        nk1: number of mesh points along the first reciprocal vector
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
        indices = list(range(nk1 * nk2 * nk3))
        norm = np.linalg.norm(ikmesh, axis=1)
        indices.sort(key=norm.__getitem__)
        ikmesh = ikmesh[indices]
    try:
        return ikmesh + 0.5 * np.array(shift)
    except ValueError as err:
        raise ValueError("expected Iterable for shift, got %s" % type(shift)) from err


def join_ksymbol_strings(ksymbols_segments: list[tuple[str, str]]) -> list[str]:
    """reserved interface for joining adjacent k-point label segments"""


def format_ksymbols(symbols, engine: str):
    """Format plain k-point symbols for matplotlib or Grace.

    Args:
        symbols (sequence of str or None): Special-point labels, including Greek
            names and discontinuous junctions such as K|U. None is preserved.
        engine (str): plt or grace.

    Returns:
        list of str or None: Backend-formatted labels in the original order.

    Raises:
        ValueError: If engine is unknown and symbols is not None.
    """
    from mushroom.core.ioutils import greeks

    if symbols is None:
        return None
    if engine not in ("plt", "grace"):
        raise ValueError("Unknown engine: {}".format(engine))
    result = []
    for symbol in symbols:
        if "$" in symbol:
            result.append(symbol)
            continue
        parts = []
        for part in symbol.split("|"):
            name = part.lstrip("\\").capitalize()
            if name in greeks:
                part = "\\" + name
                if engine == "plt":
                    part = "$" + part + "$"
            parts.append(part)
        result.append("|".join(parts))
    return result


def split_kpath_breaks(special_x, symbols) -> tuple[list[float], list[str]]:
    """Return positions and labels for discontinuous path junctions.

    Args:
        special_x (sequence of float): Special-point abscissae, shape (nspecial,),
            in the path's plotting units (possibly normalized).
        symbols (sequence of str or None): Corresponding labels; a vertical bar
            denotes a discontinuous junction. None produces empty outputs.

    Returns:
        tuple: Lists of abscissae and labels containing a vertical bar.
    """
    pairs = [] if symbols is None else [(x, s) for x, s in zip(special_x, symbols) if "|" in s]
    return [x for x, _ in pairs], [s for _, s in pairs]
