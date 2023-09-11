# -*- coding: utf-8 -*-
"""plane-wave basis related functionality"""
from itertools import product
from typing import Sequence
import numpy as np
from mushroom.core.typehint import Latt3T3, RealVec3D, IntVec3D
from mushroom.core.unit import LengthUnit, EnergyUnit
from mushroom.core.crystutils import get_recp_latt
from mushroom.core.logger import loggers

_logger = loggers['pw']


class PWBasis(LengthUnit, EnergyUnit):
    """plane-wave basis

    Args:
        cutoff (float) : cut-off energy
        latt (Latt3T3) : real-space lattice vectors
        eunit, lunit (str): unit of cutoff and lattice vectors input
        order_kind
    """
    known_order_kind = (None, "vasp")

    def __init__(self,
                 cutoff: float,
                 latt: Latt3T3,
                 eunit: str = "ry",
                 lunit: str = "au",
                 order_kind: str = None):
        LengthUnit.__init__(self, lunit=lunit)
        EnergyUnit.__init__(self, eunit=eunit)
        self.latt = np.array(latt)
        self.cutoff = cutoff
        # convert to Ryberg and Bohr after initialization
        self.eunit = "ry"
        self.lunit = "bohr"
        self._check_order_kind(order_kind)
        self.order_kind = order_kind

    @classmethod
    def _check_order_kind(cls, order_kind):
        if order_kind not in cls.known_order_kind:
            raise ValueError("unknown order kind {}".format(order_kind))

    @property
    def b(self):
        """reciprocal vectors"""
        return get_recp_latt(self.latt)

    @property
    def blen(self):
        """reciprocal vectors"""
        return np.linalg.norm(get_recp_latt(self.latt), axis=1)

    @property
    def eunit(self):
        """energy unit"""
        return self._eunit.lower()

    @eunit.setter
    def eunit(self, new: str):
        coef = self._get_eunit_conversion(new.lower())
        if coef != 1:
            self.cutoff *= coef
            self._eunit = new

    @property
    def gmax(self):
        """Gmax in Rydberg square root unit"""
        return np.sqrt(self.cutoff)

    @property
    def lunit(self):
        """length unit"""
        return self._lunit.lower()

    @lunit.setter
    def lunit(self, new: str):
        coef = self._get_lunit_conversion(new.lower())
        if coef != 1:
            self.latt = self.latt * coef
            self._lunit = new

    def get_ipw(self, kpt: RealVec3D, order_kind: str = None, symmetrize: bool = False):
        """get index of planewave basis at kpoint ``kpt``

        Args:
            kpt (ndarray, (3,)): the kpoint vector in the reciprocal lattice unit
            order_kind (str)
            is_real (bool): if wave function to expand is real.
        """
        try:
            np.add(kpt, np.zeros(3))
        except ValueError as err:
            raise ValueError("invalid kpoint vector") from err
        nmax = list(int(x) + 1 for x in self.gmax * np.reciprocal(self.blen))
        if order_kind is None:
            order_kind = self.order_kind
        else:
            self._check_order_kind(order_kind)
        if order_kind is None:
            ipw = np.array(
                tuple(product(*map(lambda n: range(-n, n + 1), nmax))))
            folded = ()
        if order_kind == "vasp":
            nmax.reverse()
            ipw = np.array(list(list(reversed(xyz)) for xyz in
                                product(*map(lambda n: [(n + i) % (2 * n + 1) - n for i in range(2 * n + 1)],
                                             nmax))))
        indices = np.linalg.norm(np.dot(ipw + kpt, self.b),
                                 axis=1) <= self.gmax
        ipw = ipw[indices, :]
        folded = ()
        if symmetrize:
            # TODO get symmetry operations from spglib
            symops = None
            folded = symmetrize_G(ipw, kpt, symops)
        return ipw, folded


def symmetrize_G(ipw: Sequence[IntVec3D], kpt: RealVec3D, symops: dict):
    """symmetrize G-vectors according to symops"""
    # TODO consider symmetries
    raise NotImplementedError


def fold_small_G_semisphere(ipw: Sequence[IntVec3D], kpt: RealVec3D):
    """find the G-vectors that can be folded back to positive axis

    if kpt is Gamma point, those Gx<0 are folded

    Args:
        ipw (ndarray)
        kpt (ndarray)

    Returns:
        tuple, each member (index of nega_G, index of correspond_posi_G)
    """
    folded = []
    inverse = np.array([-1, -1, -1])
    _logger.debug("ipw = %r", ipw)
    _logger.debug("> len(ipw) = %r", len(ipw))
    _logger.debug("kpt = %r", kpt)
    if np.allclose(kpt, 0.0):
        i_smallGs = np.where(ipw[:, 0] < 0)[0]
    else:
        # counting the Gi<0 and Gi>0 for i=x,y,z
        counts_nega = [np.count_nonzero(ipw[:, i] < 0) for i in range(3)]
        counts_posi = [np.count_nonzero(ipw[:, i] > 0) for i in range(3)]
        _logger.debug("positive Gs: %r", counts_posi)
        _logger.debug("negative Gs: %r", counts_nega)
        imax = np.argmax(np.min(np.stack([counts_nega, counts_posi]), axis=1))
        nnega = counts_nega[imax]
        nposi = counts_posi[imax]
        # fold negative back
        if nposi > nnega:
            _logger.debug("folding negative back, axis = %d", imax)
            i_smallGs = np.where(ipw[:, imax] < 0)[0]
        # fold positive back
        else:
            _logger.debug("folding positive back, axis = %d", imax)
            i_smallGs = np.where(ipw[:, imax] > 0)[0]
    smallGs_foled = ipw[i_smallGs, :] * inverse
    _logger.debug("index of G to fold: %r", i_smallGs.flatten())
    _logger.debug("G-vectors to fold to: %r", smallGs_foled)
    for ismG, smGf in zip(i_smallGs, smallGs_foled):
        _logger.debug("searching %r", smGf)
        folded.append((ismG, np.where(np.all(np.equal(ipw, smGf), axis=1))[0][0]))

    return tuple(folded)
