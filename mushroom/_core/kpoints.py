#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""utilities related to k-mesh"""
import numpy as np

class KPath:
    """object to manipulate path in reciprocal k space

    Special kpoints are recognized automatically.

    Args:
        kpts (list): the coordinates of k points
        recp_latt (3x3 array): the reciprocal lattice vectors, [b1, b2, b3].
            If parsed, it will be used to convert the kpts to Cartisian coordiantes.
    """

    def __init__(self, kpts, recp_latt=None):
        self._nkpts = len(kpts)
        if np.shape(kpts) != (self._nkpts, 3):
            raise ValueError("bad shape of parsed kpoints")
        self.kpts = np.array(kpts)
        if recp_latt is not None:
            self.kpts = np.matmul(kpts, recp_latt)
        self._ksegs = None
        self._find_ksegs()
        self._x = None
        self._special_x = None

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
            x = accumu_l + np.linalg.norm(self.kpts[st+skip:ed+1, :] - self.kpts[st, :], axis=1)
            xs.extend(x)
            accumu_l += l
        self._x = np.array(xs)
        self._special_x = self._x[ispks]

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
            if ed - st >= 2:
                ksegs.append((st, ed-1))
            st = ed - 1
        # meet same point, skip it
        if np.isclose(dotprod[ed-2], 0.):
            st += 1
            ed += 1
        ed += 1
    if ed - st >= 2:
        ksegs.append((st, ed-1))
    return ksegs
