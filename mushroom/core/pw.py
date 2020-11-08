# -*- coding: utf-8 -*-
"""plane-wave basis related functionality"""
from itertools import product
import numpy as np
from mushroom.core.typehint import Latt3T3, RealVec3D
from mushroom.core.unit import LengthUnit, EnergyUnit
from mushroom.core.crystutils import get_recp_latt

class PWBasis(LengthUnit, EnergyUnit):
    """plane-wave basis
    Args:
        cutoff (float) : cut-off energy
        latt (Latt3T3) : real-space lattice vectors
        eunit, lunit (str): unit of cutoff and lattice vectors input
    """
    def __init__(self, cutoff: float, latt: Latt3T3,
                 eunit: str = "ry", lunit: str = "au", order_kind: str = None):
        LengthUnit.__init__(self, lunit=lunit)
        EnergyUnit.__init__(self, eunit=eunit)
        self.latt = np.array(latt)
        self.cutoff = cutoff
        # convert to Ryberg and Bohr after initialization
        self.eunit = "ry"
        self.lunit = "bohr"
        self.order_kind = order_kind

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

    def get_ipw(self, kpt: RealVec3D, order_kind=None):
        """get index of planewave basis at kpoint ``kpt``

        Args:
            kpt (ndarray, (3,)): the kpoint vector in the reciprocal lattice unit
        """
        try:
            np.add(kpt, np.zeros(3))
        except ValueError as err:
            raise ValueError("invalid kpoint vector") from err
        nmax = list(int(x) for x in self.gmax * np.reciprocal(self.blen))
        if order_kind is None:
            order_kind = self.order_kind
        if order_kind is None:
            ipw = np.array(tuple(product(*map(lambda n: range(-n, n+1), nmax))))
        elif order_kind == "vasp":
            nmax.reverse()
            ipw = np.array(list(list(reversed(xyz)) for xyz in \
                                product(*map(lambda n: [(n+i) % (2*n+1) - n for i in range(2*n+1)],
                                              nmax))))
        else:
            raise NotImplementedError("unsupport order kind {}".format(order_kind))
        indices = np.linalg.norm(np.dot(ipw+kpt, self.b), axis=1) <= self.gmax
        return ipw[indices, :]



