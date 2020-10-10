# -*- coding: utf-8 -*-
"""density of states object"""
import numpy as np

from mushroom._core.unit import EnergyUnit
from mushroom._core.logger import create_logger

_logger = create_logger(__name__)
del create_logger

KEYS_DOS_PROJ = ("atms", "prjs", "pdos")
"""Tuple. Required keys for projected DOS input

"atms": a list of strings

"prjs": a list of strings

"pdos": array-like, floats as elements. 
The shape should be (nedos, nspins, natms, nprjs)
"""

class DosError(Exception):
    """exception for density of states object"""

class DensityOfStates(EnergyUnit):
    """class for analyzing density of states (DOS) data

    The energy grids of DOS and total DOS are required.
    The energy grids should be 1d array-like object, with ``nedos`` as length.
    The shape of total DOS should be (nedos, nspins)

    Args:
        egrid (1d-array-like)
        tdos (2d-array-like) : total density of states, (nspins, nedos)
        efermi (float)

    Optional args:
        unit ('ev','ry','au'): the unit of the energy grid points, in lower case.
        projection (dict): keyword arguments to parse local or projected DOS.
            It should have three keys, "atms", "prjs" and "pdos"
    """
    _dtype = 'float64'

    def __init__(self, egrid, tdos, efermi=0.0, unit='ev', **projection):
        # check shape consistency
        try:
            shape_e = np.shape(egrid)
            shape_tdos = np.shape(tdos)
            assert len(shape_e) == 1
            assert len(shape_tdos) == 2
            assert shape_tdos[1] == shape_e[0]
        except AssertionError:
            raise DosError(
                'Inconsistent shape: edos {}, DOS {}'.format(shape_e, shape_tdos))
        EnergyUnit.__init__(self, eunit=unit)
        self._egrid = np.array(egrid, dtype=self._dtype)
        self._efermi = efermi
        self._nedos, self._nspins = shape_tdos
        self._tdos = np.array(tdos, dtype=self._dtype)
        self._atms = None
        self._pdos = None
        self._prjs = None
        self._parse_proj(**projection)

    def _parse_proj(self, **projection):
        """parse the projected DOS information
        """
        if projection:
            try:
                for k in KEYS_DOS_PROJ:
                    if k not in projection:
                        raise KeyError
                self._atms = projection["atms"]
                self._prjs = projection["prjs"]
                pdos = projection["pdos"]
                natms = len(self._atms)
                nprjs = len(self._prjs)
                if np.shape(pdos) != (self._nspins, self._nedos, natms, nprjs):
                    raise TypeError 
                self._pdos = np.array(pdos, dtype=self._dtype)
            except (ValueError, KeyError, TypeError) as err:
                raise DosError("inconsistent pdos (%s) input")

    @property
    def has_pdos(self):
        """check if projected DOS is available"""
        if self._pdos is not None:
            return True
        return False

    @property
    def unit(self):
        """unit of band energies"""
        return self._eunit

    @unit.setter
    def unit(self, newu):
        coef = self._get_eunit_conversion(newu)
        arrays = [self._egrid,]
        if coef != 1:
            self._efermi *= coef
            for item in arrays:
                item *= coef
            self._eunit = newu.lower()

    @property
    def nedos(self):
        """int. number of energy grid"""
        return self._nedos

    @property
    def nspins(self):
        """int. number of spin channels"""
        return self._nspins

    @property
    def efermi(self):
        """float. Fermi energy"""
        return self._efermi

    @property
    def tdos(self):
        """array, shape (nspins, nedos). total density of states"""
        return self._tdos

    @property
    def egrid(self):
        """array, shape (nedos,). energy grid points"""
        return self._egrid

