# -*- coding: utf-8 -*-
"""density of states object"""
import numpy as np

from mushroom._core.unit import EnergyUnit
from mushroom._core.logger import create_logger
from mushroom._core.data import print_2d_data

_logger = create_logger(__name__)
del create_logger

KEYS_DOS_PROJ = ("atms", "prjs", "pdos")
"""Tuple. Required keys for projected DOS input

atms: a list of strings

prjs: a list of strings

pdos: array-like, floats as elements. 
The shape should be (nedos, nspins, natms, nprjs)
"""

class DosError(Exception):
    """exception for density of states object"""

class DensityOfStates(EnergyUnit):
    """class for analyzing density of states (DOS) data

    The energy grids of DOS and total DOS are required.
    The energy grids should be 1d array-like object, with ``nedos`` as length.
    The shape of total DOS should be (nspins, nedos)

    Args:
        egrid (1d-array-like) : energy grids
        tdos (2d-array-like) : total density of states, (nspins, nedos)
        efermi (float) : fermi energy

    Optional args:
        unit ('ev','ry','au'): the unit of the energy grid points, in lower case.
        projection (dict): keyword arguments to parse local or projected DOS.
            Generally, three keys are required, "atms", "prjs" and "pdos".
            At initialization, pdos is necessary, but atms and prjs may not be parsed.
            They can be parsed later by simply setting self.atms and self.prjs.
    """
    _dtype = 'float64'

    def __init__(self, egrid, tdos, efermi=0.0, unit='ev', **projection):
        try:
            shape_e = np.shape(egrid)
            shape_tdos = np.shape(tdos)
            assert len(shape_e) == 1
            assert len(shape_tdos) == 2
            assert shape_tdos[1] == shape_e[0]
        except AssertionError:
            info = 'Inconsistent shape, egrid {} vs tdos {}'.format(shape_e, shape_tdos)
            raise DosError(info)
                
        EnergyUnit.__init__(self, eunit=unit)
        self._egrid = np.array(egrid, dtype=self._dtype)
        self._efermi = efermi
        self._nedos, self._nspins = shape_tdos
        self._tdos = np.array(tdos, dtype=self._dtype)

        self._pdos = None
        self._atms = None
        self._prjs = None
        self._natms = 0
        self._nprjs = 0
        self.parse_proj(**projection)

    def parse_proj(self, pdos=None, atms=None, prjs=None):
        """parse the projected DOS information

        Args:
            keyword argument:
        """
        if pdos is None:
            return
        try:
            shape = np.shape(pdos)
            if shape[:2] != (self._nspins, self._nedos) or len(shape) != 4:
                raise TypeError

            self._atms = atms
            self._prjs = prjs
            if self._atms:
                self._natms = len(self._atms)
            if self._prjs:
                self._nprjs = len(self._prjs)
            natms, nprjs = shape[2:]
            if natms:
                if natms != self._natms:
                    raise ValueError
                self._nprjs = nprjs
            if nprjs:
                if nprjs != self._nprjs:
                    raise ValueError
                self._natms = natms
            self._pdos = np.array(pdos, dtype=self._dtype)
        except (ValueError, KeyError) as err:
            raise DosError("invalid pdos input")

    @property
    def atms(self):
        """list of str. atomic symbols"""
        return self._atms
    @atms.setter
    def atms(self, new):
        """update atomic symbols"""
        if len(new) != self._natms:
            raise ValueError("Inconsistent atms input. Should be {:d}-long".format(self._natms))
        self._atms = new
    @property
    def natms(self):
        """int. number of atoms"""
        return self._natms

    @property
    def prjs(self):
        """list of str. name of projectors"""
        return self._prjs
    @prjs.setter
    def prjs(self, new):
        if len(new) != self._nprjs:
            raise ValueError("Inconsistent prjs input. Should be {:d}-long".format(self._nprjs))
        self._atms = new
    @property
    def nprjs(self):
        """int. number of projectors"""
        return self._nprjs


    def has_pdos(self):
        """check if projected DOS is available"""
        if self._pdos is not None:
            return True
        return False

    @property
    def unit(self):
        """unit of energy grid"""
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

    def _get_dos(self, ispin=None, atms=None, prjs=None, transpose=False):
        """get the dos data

        Args:
            ispin (int) : 0 for spin-up and 1 for spin-down.
                Total dos will be returned otherwise or nspins=1
            transpose (bool) :
            atms (list) : str, atomic symbols, e.g. "Na", or int index
            prjs (list) : str, name of projectors, e.g., "s", "px", or int index

        Returns:
            array. Default structure is

                (e1, tdos1, pdosa1, pdosb1, ...)
                (e2, tdos2, pdosa2, pdosb2, ...)
                (e3, tdos3, pdosa3, pdosb3, ...)
                
            i.e., data goes fastest. If transpose is switched on, the output is

                (e1, e2, e3, ...)
                (tdos1, tdos2, tdos3, ...)
                (pdosa1, pdosa2, pdosa3, ...)
                (pdosb1, pdosb2, pdosb3, ...)

            i.e., abscissa goes fastest
        """
        if atms or prjs:
            raise NotImplementedError("pdos export is not supported yet!")
        if self.nspins == 2 and ispin in [0, 1]:
            d = np.column_stack([self._egrid, self._tdos[ispin, :]])
        else:
            d = np.column_stack([self._egrid, self._tdos.sum(axis=0)])
        if transpose:
            d = d.transpose()
        return d

    def _export_dos(self, ispin=None, atms=None, prjs=None, transpose=False, form=None, sep=None):
        """export the dos data.

        The data are separated by `sep`

        Args:
            ispin, atms, prjs, transpose: see `_get` method
            form (str or list/tuple): format string
            sep (str):
        """
        if separator is None:
            separator = ' '
        data = self._get_dos(ispin=ispin, atms=atms,
                             prjs=prjs, transpose=transpose)
        return print_2d_data(data, transpose=transpose, form=form, sep=sep)

