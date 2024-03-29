# -*- coding: utf-8 -*-
"""density of states object"""
import numpy as np

from mushroom.core.unit import EnergyUnit
from mushroom.core.data import export_2d_data
from mushroom.core.ioutils import (get_str_indices_by_iden,
                                   split_comma)
from mushroom.core.logger import loggers

__all__ = [
    "DensityOfStates",
    "split_ap",
]

_logger = loggers["dos"]

KEYS_DOS_PROJ = ("atms", "prjs", "pdos")
"""Tuple. Required keys for projected DOS input

atms: a list of strings

prjs: a list of strings

pdos: array-like, floats as elements.
The shape should be (nspins, nedos, natms, nprjs)
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
        tdos (2d-array-like) : total density of states, (nspins, nedos).
        efermi (float) : fermi energy

    Optional args:
        unit ('ev','ry','au'): the unit of the energy grid points, in lower case.
        projection (dict): keyword arguments to parse local or projected DOS.
            Generally, three keys are required, "atms", "prjs" and "pdos".
            At initialization, pdos is necessary, but atms and prjs may not be parsed.
            They can be parsed later by simply setting self.atms and self.prjs.
    """
    _dtype = 'float64'

    def __init__(self, egrid, tdos, efermi=None, pdos=None, atms=None, prjs=None,
                 unit='ev', nelect=None):
        try:
            shape_e = np.shape(egrid)
            shape_tdos = np.shape(tdos)
            assert len(shape_e) == 1
            assert len(shape_tdos) == 2
            assert shape_tdos[1] == shape_e[0]
        except AssertionError as err:
            info = 'Inconsistent shape, egrid {} vs tdos {}'.format(shape_e, shape_tdos)
            raise DosError(info) from err

        EnergyUnit.__init__(self, eunit=unit)
        self._egrid = np.array(egrid, dtype=self._dtype)
        if efermi is not None:
            self._efermi = efermi
        elif nelect is None:
            self._efermi = 0.0
        else:
            raise NotImplementedError("decide efermi by electron number is not supported yet")
        self._nspins, self._nedos = shape_tdos
        self._tdos = np.array(tdos, dtype=self._dtype)

        self._pdos = None
        self._atms = None
        self._prjs = None
        self._natms = 0
        self._nprjs = 0
        if pdos is not None:
            self.parse_proj(pdos=pdos, atms=atms, prjs=prjs)

    def parse_proj(self, pdos=None, atms=None, prjs=None):
        """parse the projected DOS information

        Args:
            keyword argument:
        """
        if pdos is None:
            _logger.warning("no projected dos info parsed. skip")
            return
        shape = np.shape(pdos)
        if shape[:2] != (self._nspins, self._nedos) or len(shape) != 4:
            raise DosError("bad pdos shape: {}".format(shape))

        self._natms, self._nprjs = shape[2:]
        if atms is not None:
            natms = len(atms)
            if natms != self._natms:
                raise DosError("inconsistent atms input {}".format(atms))
            self._atms = atms
        if prjs is not None:
            nprjs = len(prjs)
            if nprjs != self._nprjs:
                raise DosError("inconsistent prjs input {}".format(prjs))
            self._prjs = prjs
        self._pdos = np.array(pdos, dtype=self._dtype)
        _logger.info("Read projected density of states")

    @property
    def atms(self):
        """list of str. atomic symbols"""
        return self._atms

    @atms.setter
    def atms(self, new):
        if self._pdos is None:
            raise DosError("no projected dos found")
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
        if self._pdos is None:
            raise DosError("no projected dos found")
        if len(new) != self._nprjs:
            raise ValueError("Inconsistent prjs input. Should be {:d}-long".format(self._nprjs))
        self._prjs = new

    @property
    def nprjs(self):
        """int. number of projectors"""
        return self._nprjs

    @property
    def pdos(self):
        """projected DOS"""
        return self._pdos

    def has_pdos(self):
        """check if projected DOS is available"""
        return self._pdos is not None

    @property
    def unit(self):
        """unit of energy grid"""
        return self._eunit.lower()

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

    def has_proj(self):
        """if the projected dos has been parsed. anonym to has_pdos"""
        return self._pdos is not None

    def get_pdos(self, ispin=None, atm=None, prj=None):
        """get the partial dos

        Args:
            ispin (int) : 0 for spin-up and 1 for spin-down.
                Total dos will be returned otherwise or nspins=1
            atm (int, str, Sequence) : atomic identifier, either index or symbol
            prj (int, str, Sequence) : projector identifier, either index or name

        Returns:
            1-d array
        """
        if not self.has_proj():
            raise DosError("projected dos is not parsed")
        if atm is None:
            atm_ids = list(range(self.natms))
        else:
            atm_ids = self._get_atm_indices(atm)
        if prj is None:
            prj_ids = list(range(self.nprjs))
        else:
            prj_ids = self._get_prj_indices(prj)
        _logger.debug("pdos shape %r", self._pdos.shape)
        _logger.debug("extracting pdos for atms %r prjs %r",
                      atm_ids, prj_ids)
        if self.nspins == 2 and ispin in [0, 1]:
            coeff = self._pdos[ispin, :, :, :]
        else:
            coeff = self._pdos.sum(axis=0)
        coeff = np.take(coeff, indices=prj_ids, axis=2)
        coeff = np.take(coeff, indices=atm_ids, axis=1)
        coeff = np.sum(coeff, axis=(1, 2))
        return coeff

    def _get_atm_indices(self, atm):
        if self._atms is None:
            if isinstance(atm, int):
                return [atm,]
            if isinstance(atm, (list, tuple)):
                has_str = any(isinstance(a, str) for a in atm)
                if not has_str:
                    return atm
            raise ValueError("parse atms first for atom string")
        return get_str_indices_by_iden(self._atms, atm)

    def _get_prj_indices(self, prj):
        if self._prjs is None:
            if isinstance(prj, int):
                return [prj,]
            if isinstance(prj, (list, tuple)):
                has_str = any(isinstance(p, str) for p in prj)
                if not has_str:
                    return prj
            raise ValueError("parse prjs first for projector string")
        return get_str_indices_by_iden(self._prjs, prj)

    def get_tdos(self, ispin: int = None, reverse_spindn: bool = False):
        """get the total dos data

        Args:
            ispin (int) : the spin channel, can be 0 or 1.
                Left as None to return all spin channels.
                Total dos summed from both spin channel (nspins=2) will be returned,
                if ispin is negative.
            reverse_spindn (bool): when set True, the density of states in the second
                channel (when available) will be multiplied by -1.
                Useful for plot purpose

        Returns:
            array.
        """
        if ispin is None:
            if reverse_spindn and self.nspins == 2:
                mask = np.ones(self._tdos.shape)
                mask[1, :] = -1
                return self._tdos * mask
            return self._tdos
        if isinstance(ispin, int):
            if ispin < 0:
                return self._tdos.sum(axis=0)
            if ispin in range(self.nspins):
                return self._tdos[ispin, :]
        raise ValueError(f"invalid spin channel: {ispin}")

    def export_tdos(self, ispin=None, reverse_spindn=False, transpose=False, form=None, sep=None):
        """export the total dos data to a list of strings

        The data are separated by `sep`

        Args:
            ispin, atms, prjs: see `get_tdos` method
            form (str or list/tuple): format string
            transpose (bool) : True for array (egrid, dos1, dos2)
                False for (xa, xb, xc).
            sep (str):

        Returns:
            list of string. each string is one line as

            Default structure is

                "e1[sep]tdosup1[sep]tdosdn1[sep]"
                "e2[sep]tdosup2[sep]tdosdn2[sep]"
                "e3[sep]tdosup3[sep]tdosdn3[sep]"

            i.e., data goes fastest. If transpose is switched on, the output is

                "e1[sep]e2[sep]e3[sep]..."
                "tdosup1[sep]tdosup2[sep]tdosup3[sep]..."
                "tdosdn1[sep]tdosdn2[sep]tdosdn3[sep]..."

            i.e., abscissa goes fastest
        """
        tdos = self.get_tdos(ispin=ispin, reverse_spindn=reverse_spindn)
        if len(tdos.shape) == 1:
            data = np.stack([self._egrid, tdos])
        elif len(tdos.shape) == 2:
            data = np.stack([self._egrid, *tdos])
        else:
            raise TypeError("tdos shape is wrong, contact developer")
        return export_2d_data(data, transpose=transpose, form=form, sep=sep)


def split_ap(ap: str):
    """split an atom-projector string into lists containing corresponding identifiers

    An atom-projector string is a string with the format as

        atom:projector:bands

    each could be:

        - atom: "S", "Fe", 0, 1, "B,N", "0,1,2"
        - projector: "s", "p,d", "px", "dxy,dz2", 0.

    Returns:
        list, list
    """
    if " " in ap:
        raise ValueError("whitespace is not allowed in atom-projector string, got", ap)
    try:
        a, p = ap.split(":")
    except ValueError as err:
        raise ValueError("should contain two colons") from err

    return split_comma(a, int), split_comma(p, int)
