# -*- coding: utf-8 -*-
"""Module that defines class and utilities for band structure
"""
import re
from collections.abc import Iterable
from itertools import permutations, product
from typing import Sequence, Union
from copy import deepcopy
from numbers import Real

import numpy as np

from mushroom.core.logger import loggers
from mushroom.core.unit import EnergyUnit
from mushroom.core.ioutils import get_str_indices_by_iden, split_comma
from mushroom.core.typehint import Key

__all__ = [
    "BandStructure",
    "split_apb",
]

# eigen, occ (array): shape (nspins, nkpt, nbands)
DIM_EIGEN_OCC = 3
"""int. Required dimension of eigenvalues and occupation numbers
"""

KEYS_BAND_PROJ = ("atms", "prjs", "pwav")
"""tuple. Required keys for wave projection input
"""

BAND_STR_PATTERN = re.compile(r"[vc]bm([-+][\d]+)?")

# DIM_PWAVE = 5
# '''pwave (array): shape (nspins, nkpt, nbands, natoms, nprojs)'''

THRES_EMP = 1.0E-3
THRES_OCC = 1.0 - THRES_EMP
# threshold of degeneracy in eV
THRES_DEGENERATE = 5.0E-4

AtmPrjToken = Union[Key, Sequence[Key]]

_logger = loggers["bs"]


class BandStructureError(Exception):
    """exception for band structure"""


class BandStructure(EnergyUnit):
    """Base class for analyzing band structure data.

    The eigenvalues should be parsed in a shape of
    (nspins, nkpts, nbands).
    The dimensions are automatically checked.
    Exception will be raised if their shapes are inconsistent.

    Optional keyword arguments, if parsed, should have consistent
    shape with the required arguments.
    Exception will be raised if their shapes are inconsistent.

    If no occ is parsed and efermi is parsed, the occupation number
    will be calculated according to zero-temperature occupation,
    i.e. occupied (1.0) if eigen < efermi

    Args:
        eigen (array-like) : the energy (eigenvalues) of all bands to be considered

    Optional args:
        occ (array-like) : the occupation numbers of all bands
        weight (array-like) : the weights of each kpoint, 1-d array,
            either integer weight or scaled weight. default to 1.0
        unit ('ev','ry','au'): the unit of the eigenvalues
        efermi (float): the Fermi level.
            If not parsed, the valence band maximum will be used.
        pwav (array-like): wave projection information
        atms, prjs (list): specifies the names of atoms and projectors in wave projection
        use_occ_only (bool): By default, both eigenvalues and occupation numbers will be
            used to find the band edges.
            if True, only the occupation number will be used.

    Attributes:
    """
    _dtype = "float64"
    # pylint: disable=R0912,R0915

    def __init__(self, eigen, occ=None, weight=None, unit: str = 'ev', efermi: float = None,
                 pwav=None, atms: Sequence[str] = None, prjs: Sequence[str] = None,
                 use_occ_only: bool = False):
        shape_e = np.shape(eigen)
        if occ is not None:
            consist = [len(shape_e) == DIM_EIGEN_OCC, shape_e[0] <= 2]
            if not all(consist):
                info = "Bad eigen shape"
                _logger.error(info)
                raise BandStructureError
        self._nspins, self._nkpts, self._nbands = shape_e
        # if weight is manually parsed
        if weight is not None:
            shape_w = np.shape(weight)
            consist = [len(shape_w) == 1, shape_w[0] == shape_e[1]]
            if not all(consist):
                _logger.error("invalid weight shape")
                raise BandStructureError
        else:
            weight = np.ones(self._nkpts)

        try:
            self._eigen = np.array(eigen, dtype=self._dtype)
            self._weight = np.array(weight, dtype=self._dtype)
        except TypeError as err:
            _logger.error("fail to convert eigen/weight to ndarray")
            raise BandStructureError from err

        EnergyUnit.__init__(self, eunit=unit)
        # self._emulti = {1: 2, 2: 1}[self._nspins]
        # One may parse the kpoints with all zero weight for band calculation
        # In this case, reassign with unit weight
        if np.isclose(np.sum(self._weight), 0.0):
            self._weight[:] = 1.0
        # set occupation numbers
        self._occ = None
        self._efermi = efermi
        # channel: ispin, ikpt
        self._is_metal = None
        self._nelect_sp_kp = None
        self._vbm_sp_kp = None
        self._cbm_sp_kp = None
        self._vbm_sp = None
        self._cbm_sp = None
        self._vbm = None
        self._cbm = None
        self._ivbm_sp_kp = None
        self._icbm_sp_kp = None
        self._ivbm_sp = None
        self._icbm_sp = None
        self._ivbm = None
        self._icbm = None
        self._nelect_sp = None
        self._nelect = None
        self._has_infty_cbm = False
        self._vbm = None
        self._cbm = None
        self._band_width = None
        self._band_edges_use_occ_only = use_occ_only

        self._bandedge_calculated = False

        # compute occupations from eigen and efermi
        # NOTE: zero temperature is used here
        if occ is None:
            if efermi is not None:
                occ = np.zeros(self.eigen.shape)
                occ[self.eigen <= efermi] = 1.0
                self._set_occupations(occ)
        else:
            self._set_occupations(occ)

        _logger.info("Read bandstructure. Dimensions")
        _logger.info(">> nspins = %d, nkpts = %d, nbands = %d", self._nspins, self._nkpts, self._nbands)

        self._pwav = None
        self._atms = None
        self._prjs = None
        self._natms = 0
        self._nprjs = 0
        if pwav is not None:
            self.parse_proj(pwav=pwav, atms=atms, prjs=prjs)

    def _set_occupations(self, occ, allow_reset: bool = False):
        """set occupation numbers

        Args:
            occ (ndarray): occupation numbers, (nspins, nkpts, nbands)
        """
        if self._occ is not None and not allow_reset:
            raise AttributeError("occupations are already set")
        try:
            shape_o = np.shape(occ)
        except ValueError as err:
            raise ValueError("can not retrive the shape of input occupations") from err
        shape_e = (self._nspins, self._nkpts, self._nbands)
        if shape_e != shape_o:
            info = "inconsistent eigen/occ shapes: {}, {}".format(shape_e, shape_o)
            _logger.error(info)
            raise BandStructureError
        self._occ = np.array(occ, dtype=self._dtype)
        # self._nelect_sp_kp = np.sum(self._occ, axis=2) * self._emulti
        self._nelect_sp_kp = np.sum(self._occ, axis=2)
        self._nelect_sp = np.dot(self._nelect_sp_kp, self._weight) / np.sum(self._weight)
        self._nelect = np.sum(self._nelect_sp)
        # since occupation is changed, band edges need to be recomputed
        _logger.info("occupation (re)set, reset band edges")
        self._bandedge_calculated = False

    def _set_occupations_by_efermi(self, efermi: float, unit: str = "ev", allow_reset: bool = False):
        occ = np.zeros(self.eigen.shape)
        efermi = efermi / self._get_eunit_conversion(unit)
        # TODO: more occupation methods
        occ[self.eigen <= efermi] = 1.0
        self._set_occupations(occ, allow_reset=allow_reset)

    def _set_occupations_by_states(self, n_states: int, allow_reset: bool = False):
        occ = np.zeros(self.eigen.shape)
        occ[:, :, :n_states] = 1.0
        self._set_occupations(occ, allow_reset=allow_reset)

    def reset_occupations(self, occ=None, efermi=None, n_states: int = None, unit: str = "ev"):
        if occ is not None:
            self._set_occupations(occ, True)
        elif efermi is not None:
            self._set_occupations_by_efermi(efermi, unit=unit, allow_reset=True)
        elif n_states is not None:
            self._set_occupations_by_states(n_states, allow_reset=True)
        else:
            raise ValueError("occ, efermi, nelec are None. Please specify one of them.")

    def get_band_indices(self, *bands):
        '''Filter the band indices in ``bands``.

        If no indices is specified, return all available band indices.

        Args:
            bands (int or str): the band identifier.
                can be band indices (int), or strings like "cbm", "vbm",
                "cbm-5", "vbm+2", etc.

        Returns:
            list
        '''
        b = []
        for ib in bands:
            b.append(self._convert_band_iden(ib))
        return b

    def prune_bands(self, remove_from_start: int = 0, remove_from_end: int = 0):
        """Remove unwanted bands from beginning or from the end

        Args:
            remove_from_start (int)
            remove_from_end (int)

        Returns:
            None
        """
        if remove_from_start == 0 and remove_from_end == 0:
            return
        if remove_from_start < 0:
            raise ValueError("remove_from_start cannot be negative: %d" % remove_from_start)
        if remove_from_end < 0:
            raise ValueError("remove_from_end cannot be negative: %d" % remove_from_end)

        ed = self.nbands - remove_from_end
        self._eigen = self._eigen[:, :, remove_from_start:ed]
        self._occ = self._occ[:, :, remove_from_start:ed]
        if self._pwav is not None:
            self._pwav = self._pwav[:, :, remove_from_start:ed, :, :]

        # reset dimension and bands
        self._nspins, self._nkpts, self._nbands = np.shape(self._eigen)
        self._bandedge_calculated = False

    def _convert_band_iden(self, band_iden: Union[int, str]) -> int:
        """convert a string of band identifier, like "vbm", "cbm-2", "vbm+3"
        to the correpsonding band index.

        Args:
            band_str (int, str)

        Returns:
            int
        """
        if isinstance(band_iden, int):
            return band_iden
        try:
            # when parsed a string of integer
            return int(band_iden)
        except ValueError:
            if BAND_STR_PATTERN.match(band_iden):
                ref = {"v": self.ivbm[-1], "c": self.icbm[-1]}[band_iden[0]]
                if len(band_iden) == 3:
                    return ref
                n = int(re.split(r"[-+]", band_iden)[-1])
                if band_iden[3] == '-':
                    ib = ref - n
                else:
                    ib = ref + n
                # check if the band index is valid
                if 0 <= ib < self.nbands:
                    return ib
        raise ValueError(f"unrecognized band identifier {band_iden}")

    @property
    def unit(self):
        """unit of band energies"""
        return self._eunit.lower()

    @unit.setter
    def unit(self, newu: str):
        coef = self._get_eunit_conversion(newu)
        to_conv = [
            self._eigen,
            self._vbm_sp, self._vbm_sp_kp,
            self._cbm_sp, self._cbm_sp_kp,
        ]
        if coef != 1:
            if self._efermi is not None:
                self._efermi *= coef
            if self._vbm is not None:
                self._vbm *= coef
            if self._cbm is not None:
                self._cbm *= coef
            for item in to_conv:
                if item is not None:
                    item *= coef
            self._eunit = newu.lower()

    @property
    def eigen(self):
        '''Array. Eigenvalues, (nspins, nkpts, nbands)'''
        return self._eigen

    @property
    def occ(self):
        '''Array. Occupation numbers, (nspins, nkpts, nbands)'''
        return self._occ

    @property
    def weight(self):
        '''Array. kpoints weight (int like), (nkpts, )'''
        return self._weight

    @property
    def efermi(self):
        '''float. The energy of Fermi level.

        If fermi energy was not manually set and occ is available, it will be computed
        as the valence band maximum of first spin channel.

        None, if neither occupation nor explicit fermi energy was parsed
        '''
        if self._efermi is None:
            return self.vbm
        return self._efermi

    @property
    def nelect(self):
        '''Float. Total number of electrons'''
        return self._nelect

    @property
    def nspins(self):
        '''Int. number of spin channels'''
        return self._nspins

    @property
    def nkpts(self):
        '''Int. number of kpoints'''
        return self._nkpts

    @property
    def nbands(self):
        '''Int. number of bands'''
        return self._nbands

    @property
    def nstates(self):
        '''Int. number of bands'''
        return self._nbands

    def parse_proj(self, pwav=None, atms: Sequence[str] = None, prjs: Sequence[str] = None):
        """Parse the partial wave information
        """
        if pwav is None:
            _logger.warning("no partial wave info parsed. skip")
            return
        shape = np.shape(pwav)
        if shape[:3] != (self._nspins, self._nkpts, self._nbands) or len(shape) != 5:
            raise BandStructureError("invalid shape of pwav")

        self._natms, self._nprjs = shape[3:]
        if atms is not None:
            natms = len(atms)
            if natms != self._natms:
                raise BandStructureError("inconsistent atms input {}".format(atms))
            self._atms = atms
            _logger.info("Read atoms of partial wave, dimension = %s", natms)
        if prjs is not None:
            nprjs = len(prjs)
            if nprjs != self._nprjs:
                raise BandStructureError("inconsistent prjs input {}".format(prjs))
            self._prjs = prjs
            _logger.info("Read projectors of partial wave, dimension = %s", nprjs)
        self._pwav = np.array(pwav, dtype=self._dtype)
        _logger.info("Read partial wave")

    def has_proj(self):
        """Bool"""
        return self._pwav is not None

    @property
    def atms(self):
        """list of strings, types of each atom. None for no atoms info"""
        return self._atms

    @atms.setter
    def atms(self, new: str):
        if self._pwav is None:
            raise BandStructureError("no partial wave found")
        if len(new) != self._natms:
            raise ValueError("Inconsistent atms input. Should be {:d}-long".format(self._natms))
        self._atms = new

    @property
    def natms(self):
        """number of atoms"""
        return self._natms

    @property
    def prjs(self):
        """list of strings, names of atomic projectors. None for no projectors info"""
        return self._prjs

    @prjs.setter
    def prjs(self, new: str):
        if self._pwav is None:
            raise BandStructureError("no partial wave found")
        if len(new) != self._nprjs:
            raise ValueError("Inconsistent prjs input. Should be {:d}-long".format(self._nprjs))
        self._prjs = new

    @property
    def nprjs(self):
        """number of projectors"""
        return self._nprjs

    @property
    def pwav(self):
        """Array, partial waves for each projector on each atom.

        shape (nspins, nkpts, nbands, natms, nprjs)

        None if no projection information was parsed.
        """
        return self._pwav

    # pylint: disable=R0912,R0915
    def compute_band_edges(self, reload: bool = False):
        '''compute the band edges on each spin-kpt channel, using occupation number

        Note:
            When nbands is too small and all bands are found to be valence bands,
            or it is the case for one spin-kpoint channel, the corresponding CB will
            be set to ``np.inf``.
            Setup of indices of CB remains, thus IndexError might be raised when trying
            get CB value from `icbm` attributes

            There could be cases that the occupied band with largest band index
            is not actually the band maximum, or something similar for empty bands,
            e.g. in perturbation theory calculation.
            This is handled by this method.
            If one insists to set the band maximum to the occupied band with largest index,
            set ``use_occ_only`` to True when creating the BandStructure object.

        Args:
            reload (bool) : redo the calculation of band edges
        '''
        if self._occ is None:
            raise BandStructureError("need occupation number before computing band edges!")
        if self._bandedge_calculated and not reload:
            return

        self._band_width = np.zeros(
            (self.nspins, self.nbands, 2), dtype=self._dtype)
        self._band_width[:, :, 0] = np.min(self._eigen, axis=1)
        self._band_width[:, :, 1] = np.max(self._eigen, axis=1)

        if self._band_edges_use_occ_only:
            self._load_band_edges_by_occ()
        else:
            self._load_band_edges_by_eigen()

        if np.max(self._ivbm_sp_kp) == np.min(self._ivbm_sp_kp):
            self._is_metal = False
        else:
            self._is_metal = True
        _logger.debug("is_metal? %s", self._is_metal)

        # set the state to ready
        self._bandedge_calculated = True

    def _load_band_edges_by_occ(self):
        is_occ = self._occ > THRES_OCC
        self._ivbm_sp_kp = np.sum(is_occ, axis=2) - 1
        _logger.debug("HOMO index per spin per kpoint")
        for i in range(self._nspins):
            _logger.debug("Spin %d: %r", i + 1, self._ivbm_sp_kp[i, :])
        # when any two indices of ivbm differ, the system is metal
        self._icbm_sp_kp = self._ivbm_sp_kp + 1
        # avoid IndexError when ivbm is the last band by imposing icbm = ivbm in this case
        ivbIsLast = self._ivbm_sp_kp == self.nbands - 1
        if np.any(ivbIsLast):
            _logger.warning("nbands %s is too small to get CB", self.nbands)
            self._icbm_sp_kp[ivbIsLast] = self.nbands - 1

        self._vbm_sp_kp = np.zeros(
            (self.nspins, self.nkpts), dtype=self._dtype)
        self._cbm_sp_kp = np.zeros(
            (self.nspins, self.nkpts), dtype=self._dtype)
        # ? maybe optimize
        for i in range(self.nspins):
            for j in range(self.nkpts):
                vb = self._ivbm_sp_kp[i, j]
                self._vbm_sp_kp[i, j] = self.eigen[i, j, vb]
                if vb == self.nbands - 1:
                    self._has_infty_cbm = True
                    info = "VBM index for spin-kpt channel (%d,%d) equals nbands. %s"
                    _logger.warning(
                        info, i + 1, j + 1, "CBM for this channel set to infinity")
                    self._cbm_sp_kp[i, j] = np.inf
                else:
                    self._cbm_sp_kp[i, j] = self.eigen[i, j, vb + 1]
        # VB indices
        self._ivbm_sp = np.array(((0, 0),) * self.nspins)
        self._vbm_sp = np.max(self._vbm_sp_kp, axis=1)
        self._ivbm_sp[:, 0] = np.argmax(self._vbm_sp_kp, axis=1)
        for i in range(self.nspins):
            ik = int(self._ivbm_sp[i, 0])
            self._ivbm_sp[i, 1] = self._ivbm_sp_kp[i, ik]
        self._ivbm = np.array((0, 0, 0))
        self._ivbm[0] = int(np.argmax(self._vbm_sp))
        self._ivbm[1:3] = self._ivbm_sp[self._ivbm[0], :]
        self._vbm = self._vbm_sp[self._ivbm[0]]
        # CB indices
        self._icbm_sp = np.array(((0, 0),) * self.nspins)
        self._cbm_sp = np.min(self._cbm_sp_kp, axis=1)
        self._icbm_sp[:, 0] = np.argmin(self._cbm_sp_kp, axis=1)
        for i in range(self.nspins):
            ik = int(self._icbm_sp[i, 0])
            self._icbm_sp[i, 1] = self._icbm_sp_kp[i, ik]
        self._icbm = np.array((0, 0, 0))
        self._icbm[0] = int(np.argmin(self._cbm_sp))
        self._icbm[1:3] = self._icbm_sp[self._icbm[0], :]
        self._cbm = self._cbm_sp[self._icbm[0]]

    # pylint: disable=R0912,R0915
    def _load_band_edges_by_eigen(self):
        is_occ = self._occ > THRES_OCC
        thres_degen = THRES_DEGENERATE / self._get_eunit_conversion("ev")

        self._vbm_sp_kp = np.zeros((self.nspins, self.nkpts), dtype=self._dtype)
        self._cbm_sp_kp = np.zeros((self.nspins, self.nkpts), dtype=self._dtype)
        self._ivbm_sp_kp = np.zeros((self.nspins, self.nkpts), dtype=int)
        self._icbm_sp_kp = np.zeros((self.nspins, self.nkpts), dtype=int)
        self._vbm_sp = np.zeros((self.nspins), dtype=self._dtype)
        self._cbm_sp = np.zeros((self.nspins), dtype=self._dtype)
        self._ivbm_sp = np.zeros((self.nspins, 2), dtype=int)
        self._icbm_sp = np.zeros((self.nspins, 2), dtype=int)
        self._ivbm = np.zeros(3, dtype=int)
        self._icbm = np.zeros(3, dtype=int)

        self._vbm_sp_kp[:, :] = -np.inf
        self._cbm_sp_kp[:, :] = np.inf
        self._vbm_sp[:] = -np.inf
        self._cbm_sp[:] = np.inf
        self._vbm = -np.inf
        self._cbm = np.inf

        # a naive way to find VBM and CBM on each spin and kpoint channel
        for isp in range(self._nspins):
            for ik in range(self._nkpts):
                for ib, ibr in zip(range(self._nbands), reversed(range(self._nbands))):
                    # use thres_degen such that when degenerate bands are met,
                    # we always use the larger (smaller) index for VBM (CBM)
                    if is_occ[isp, ik, ib] and (
                            self._eigen[isp, ik, ib] > self._vbm_sp_kp[isp, ik] or
                            abs(self._eigen[isp, ik, ib] - self._vbm_sp_kp[isp, ik]) < thres_degen):
                        self._vbm_sp_kp[isp, ik] = self._eigen[isp, ik, ib]
                        self._ivbm_sp_kp[isp, ik] = ib
                        _logger.debug("Updating VB %d %d %d %d", isp, ik, ib, self._vbm_sp_kp[isp, ik])
                    if not is_occ[isp, ik, ibr] and (
                            self._eigen[isp, ik, ibr] < self._cbm_sp_kp[isp, ik] or
                            abs(self._eigen[isp, ik, ibr] - self._cbm_sp_kp[isp, ik]) < thres_degen):
                        self._cbm_sp_kp[isp, ik] = self._eigen[isp, ik, ibr]
                        self._icbm_sp_kp[isp, ik] = ibr
                        _logger.debug("Updating CB %d %d %d %d", isp, ik, ib, self._cbm_sp_kp[isp, ik])
                if self._vbm_sp_kp[isp, ik] > self._vbm_sp[isp]:
                    self._vbm_sp[isp] = self._vbm_sp_kp[isp, ik]
                    self._ivbm_sp[isp, :] = [ik, self._ivbm_sp_kp[isp, ik]]
                if self._cbm_sp_kp[isp, ik] < self._cbm_sp[isp]:
                    self._cbm_sp[isp] = self._cbm_sp_kp[isp, ik]
                    self._icbm_sp[isp, :] = [ik, self._icbm_sp_kp[isp, ik]]
            if self._vbm_sp[isp] > self._vbm:
                self._vbm = self._vbm_sp[isp]
                self._ivbm[:] = [isp, *self._ivbm_sp[isp]]
            if self._cbm_sp[isp] < self._cbm:
                self._cbm = self._cbm_sp[isp]
                self._icbm[:] = [isp, *self._icbm_sp[isp]]
            _logger.debug("VBM of Spin %d: %r", isp + 1, self._ivbm_sp_kp[isp, :])
            _logger.debug("CBM of Spin %d: %r", isp + 1, self._icbm_sp_kp[isp, :])
        _logger.debug("global VBM: %r %f", self._ivbm[:], self._vbm)
        _logger.debug("global CBM: %r %f", self._icbm[:], self._cbm)

    def apply_scissor(self, scissor: float, force_metal: bool = False):
        """apply scissor operator and return a new BandStructure object

        Args:
            scissor (float): scissor operator, value in the same unit as current object
            force_metal (bool): scissor operator is applied anyway, even the system becomes metallic afterwards

        Returns:
            BandStructure object
        """
        gap = self.fund_gap()
        if gap < 0:
            raise NotImplementedError("Scissor operator not yet implemented for metal")
        if gap + scissor < 0 and not force_metal:
            raise ValueError("Scissor operator will leads to a metal state")
        icb = self.icbm[2]
        eigen = deepcopy(self.eigen)
        eigen[:, :, icb:] += scissor
        return type(self)(eigen, self.occ, self.weight, self.unit, self._efermi,
                          self._pwav, self._atms, self._prjs)

    def _lazy_bandedge_return(self, attr: str = None):
        """lazy return of attribute related to band edges

        Args:
            attr (str): name of attribute
        """
        self.compute_band_edges()
        if attr is None:
            return None
        v = self.__getattribute__(attr)
        if v is None:
            raise ValueError("attribute {} is not available for band".format(attr.strip("_")))
        return v

    def is_metal(self):
        """bool. True if the bandstructure belongs to a metal, False otherwise
        """
        return self._lazy_bandedge_return("_is_metal")

    @property
    def ivbm_sp_kp(self):
        """indices of valence band maximum at each spin-kpt channel

        int, shape (nspins, nkpts)
        """
        return self._lazy_bandedge_return("_ivbm_sp_kp")

    @property
    def icbm_sp_kp(self):
        """indices of conduction band minimum at each spin-kpt channel

        int, shape (nspins, nkpts)
        """
        return self._lazy_bandedge_return("_icbm_sp_kp")

    @property
    def ivbm_sp(self):
        """indices of valence band maximum per spin

        int, shape (nspins, 2), ikpt, iband
        """
        return self._lazy_bandedge_return("_ivbm_sp")

    @property
    def icbm_sp(self):
        """indices of conduction band minimum per spin

        int, shape (nspins, 2), ikpt, iband
        """
        return self._lazy_bandedge_return("_icbm_sp")

    @property
    def ivbm(self):
        """index of valence band maximum

        int, shape (3,), ispin, ikpt, iband
        """
        return self._lazy_bandedge_return("_ivbm")

    @property
    def icbm(self):
        """index of conduction band minimum

        int, shape (3,), ispin, ikpt, iband
        """
        return self._lazy_bandedge_return("_icbm")

    @property
    def vbm_sp_kp(self):
        """valiues of valence band maximum at each spin-kpt channel

        float, shape (nspins, nkpts)
        """
        return self._lazy_bandedge_return("_vbm_sp_kp")

    @property
    def cbm_sp_kp(self):
        """values of conduction band minimum at each spin-kpt channel

        float, shape (nspins, nkpts)
        """
        return self._lazy_bandedge_return("_cbm_sp_kp")

    @property
    def vbm_sp(self):
        """valiues of valence band maximum per spin

        float, shape (nspins,)
        """
        return self._lazy_bandedge_return("_vbm_sp")

    @property
    def cbm_sp(self):
        """values of conduction band minimum per spin

        float, shape (nspins,)
        """
        return self._lazy_bandedge_return("_cbm_sp")

    @property
    def vbm(self):
        """value of valence band maximum

        float
        """
        return self._lazy_bandedge_return("_vbm")

    @property
    def cbm(self):
        """value of conduction band minimum

        float
        """
        return self._lazy_bandedge_return("_cbm")

    @property
    def band_width(self):
        """the lower and upper bound of a band

        float, shape (nspins, nbands, 2)
        """
        return self._lazy_bandedge_return("_band_width")

    def direct_gaps(self):
        """Direct gap between VBM and CBM of each spin-kpt channel

        float, shape (nspins, nkpts)
        """
        return self.cbm_sp_kp - self.vbm_sp_kp

    def direct_gap_sp(self):
        """The minimal direct gap between VBM and CBM of each spin channel

        float, shape (nspins,)
        """
        return np.min(self.direct_gaps(), axis=1)

    def direct_gap(self):
        """The minimal direct gap between VBM and CBM, float"""
        return np.min(self.direct_gap_sp())

    def direct_gap_vbm(self):
        """Direct gap at VBM

        float
        """
        is_vb, ik_vb = self.ivbm[0], self.ivbm[1]
        return self.direct_gaps()[is_vb, ik_vb]

    def direct_gap_cbm(self):
        """Direct gap at CBM

        float
        """
        is_cb, ik_cb = self.icbm[0], self.icbm[1]
        return self.direct_gaps()[is_cb, ik_cb]

    def is_gap_direct(self) -> bool:
        """True if the bandstructure belongs to a direct gap material"""
        return all(self.fund_gap_sp() >= self.direct_gap())

    def fund_gap_sp(self):
        """Fundamental gap for each spin channel.

        float, shape (nspins,)
        If it is metal, it is equivalent to the negative value of bandwidth
        of the unfilled band.
        """
        return self.cbm_sp - self.vbm_sp

    def fund_gap(self):
        """Fundamental gap, float"""
        return self.cbm - self.vbm

    def fund_trans_sp(self):
        """Transition responsible for the fundamental gap in each spin channel

        int, shape (nspins, 2)
        """
        vb = np.argmax(self.vbm_sp_kp, axis=1)
        cb = np.argmin(self.cbm_sp_kp, axis=1)
        return tuple(zip(vb, cb))

    def fund_trans(self):
        """Transition responsible for the fundamental gap

        int, shape (2, 2), [0,:]: (vbm spin, vbm k), [1,:]: (cbm spin, cbm k)
        """
        shape = (self._nspins, self._nkpts)
        vb = np.unravel_index(np.argmax(self.vbm_sp_kp, axis=None), shape)
        cb = np.unravel_index(np.argmin(self.cbm_sp_kp, axis=None), shape)
        return tuple((vb, cb))

    def get_transition(self,
                       ivk: int = None,
                       ick: int = None,
                       ivb: Union[int, str] = None,
                       icb: Union[int, str] = None,
                       ispin: int = 0,
                       return_index: bool = False):
        """get the transition energy between particular transition in a spin channel

        Args:
            ivk,ick (int): the kpoint index of valence and conduction band
            ivb,icb (int,str): the band index of valence and conduction band
            ispin (int): the spin channel
            return_index (bool): also return the index
        """
        if ivb is None or ivb == "":
            ivb = "vbm"
        if icb is None or icb == "":
            icb = "cbm"
        ivb = self._convert_band_iden(ivb)
        icb = self._convert_band_iden(icb)
        if ivk is None:
            ivk = np.argmax(self.eigen[ispin, :, ivb])
        vb = self.eigen[ispin, ivk, ivb]
        if ick is None:
            ick = np.argmin(self.eigen[ispin, :, icb])
        cb = self.eigen[ispin, ick, icb]
        if return_index:
            return cb - vb, ivk, ick, ivb, icb
        return cb - vb

    def kavg_gap(self):
        """direct band gap averaged over kpoints

        float, shape (nspins,)
        """
        return np.dot(self.direct_gaps(), self._weight) / np.sum(self._weight)

    # * Projection related functions
    def effective_gap(self, ivb: int = None, icb: int = None,
                      atm_vbm: AtmPrjToken = None,
                      prj_vbm: AtmPrjToken = None,
                      atm_cbm: AtmPrjToken = None,
                      prj_cbm: AtmPrjToken = None):
        '''Compute the effective band gap between ``ivb`` and ``icb``,
        the responsible transition of which associates projector `proj_vbm` on `atom_vbm` in VB
        and `proj_cbm` on atom `atom_cbm` in CB.

        If no projection information was parsed, the inverse of the k-averaged gap inverse
        will be returned.

        Args:
            ivb (int): index of the lower band. Use VBM if not specified or is invalid index.
            icb (int): index of the upper band. Use CBM if not specified or is invalid index.
            atm_vbm (instance or sequence of Key): atom where the VB projector is located
            atm_cbm (instance or sequence of Key): atom where the CB projector is located
            prj_vbm (instance or sequence of Key): index of VB projector
            prj_cbm (instance or sequence of Key): index of CB projector

        Note:
            Spin-polarization is not considered in retriving projection coefficients.
        '''
        try:
            vb_coefs = self.get_pwav(atm_vbm, prj_vbm)
            cb_coefs = self.get_pwav(atm_cbm, prj_cbm)
        except BandStructureError as err:
            info = "unable to compute effective gap, since no partial wave is parsed. try kavg_gap"
            raise BandStructureError(info) from err
        if ivb is None or ivb not in range(self.nbands):
            vb_coef = vb_coefs[:, :, np.max(self.ivbm)]
        else:
            vb_coef = vb_coefs[:, :, ivb]
        if icb is None or icb not in range(self.nbands):
            cb_coef = cb_coefs[:, :, np.min(self.icbm)]
        else:
            cb_coef = cb_coefs[:, :, icb]
        # ! abs is added in case ivb and icb are put in the opposite
        inv = np.sum(np.abs(np.reciprocal(self.direct_gaps()) * vb_coef * cb_coef))
        if np.allclose(inv, 0.0):
            return np.infty
        return 1.0 / inv

    def get_eigen(self, indices=None):
        """get eigenvalues of particular bands

        Args:
            indices (int, str, or their Sequence): indices of band.
                None to include all bands.

        Returns:
            (nspins, nkpts, nb) with nb = len(indices)
        """
        if indices is None:
            indices = range(self.nbands)
        else:
            indices = self._get_band_indices(indices)
        return self._eigen[:, :, indices]

    def get_pwav(self, atm: AtmPrjToken = None, prj: AtmPrjToken = None, indices=None):
        """get particular partial wave for projectors `proj` on atoms `atom`

        Args:
            atm (int, str, or their Sequence)
            prj (int, str, or their Sequence)
            indices (int, str, or their Sequence): indices of band.
                None to include all bands.

        Returns:
            (nspins, nkpts, nb) with nb = len(indices)
        """
        if not self.has_proj():
            raise BandStructureError("partial wave is not parsed")
        if atm is None:
            atm_ids = list(range(self.natms))
        else:
            atm_ids = self._get_atm_indices(atm)
        if prj is None:
            prj_ids = list(range(self.nprjs))
        else:
            prj_ids = self._get_prj_indices(prj)
        if indices is None:
            indices = range(self.nbands)
        else:
            indices = self._get_band_indices(indices)
        nb = len(indices)
        if nb == 0:
            raise ValueError("no bands is specified")
        _logger.debug("pwav shape %r", self._pwav.shape)
        _logger.debug("extracting pwav for bands %r, atms %r prjs %r",
                      indices, atm_ids, prj_ids)
        coeff = np.take(self._pwav, indices=prj_ids, axis=4)
        coeff = np.take(coeff, indices=atm_ids, axis=3)
        coeff = np.sum(coeff[:, :, indices, :, :], axis=(-1, -2))
        if nb == 1:
            coeff = coeff.reshape((self.nspins, self.nkpts, 1))
        _logger.debug("extracted coeff shape %r", coeff.shape)
        return coeff

    def _get_band_indices(self, ib):
        if isinstance(ib, str):
            return [self._convert_band_iden(ib),]
        if isinstance(ib, Iterable):
            return list(map(self._convert_band_iden, ib))
        return [self._convert_band_iden(ib),]

    def _get_atm_indices(self, atm):
        if self._atms is None:
            if isinstance(atm, int):
                return [atm,]
            if isinstance(atm, Iterable):
                has_str = any(isinstance(a, str) for a in atm)
                if not has_str:
                    return atm
            raise ValueError("parse atms first for atom string")
        return get_str_indices_by_iden(self._atms, atm)

    def _get_prj_indices(self, prj):
        if self._prjs is None:
            if isinstance(prj, int):
                return [prj,]
            if isinstance(prj, Iterable):
                has_str = any(isinstance(p, str) for p in prj)
                if not has_str:
                    return prj
            raise ValueError("parse prjs first for projector string")
        return get_str_indices_by_iden(self._prjs, prj)

    def resolve(self, eres=0.01):
        """resolve band entanglements and making each band energy continuous in k

        Useful in drawing band structure with a kpath

        Args:
            eres (float): resolution of energy for grouping bands
        """
        raise NotImplementedError

    def __add__(self, y: Real):
        if isinstance(y, Real):
            if y == 0.0:
                return self
            newbs = deepcopy(self)
            newbs._eigen = newbs._eigen + y
            if newbs._efermi is not None:
                newbs._efermi += y
            newbs._bandedge_calculated = False
            return newbs
        raise TypeError("expected a Real, got {}".format(type(y)))

    def __sub__(self, y):
        if isinstance(y, type(self)):
            newbs = deepcopy(self)
            if y.nbands < newbs.nbands:
                raise ValueError("y should have bands no fewer than self, but {} < {}"
                                 .format(y.nbands, self.nbands))
            if y.nkpts != newbs.nkpts:
                raise ValueError("y should have the same kpoints as self, but {} != {}"
                                 .format(y.nkpts, self.nkpts))
            if y.nspins != newbs.nspins:
                raise ValueError("y should have the same spins as self, but {} != {}"
                                 .format(y.nspins, self.nspins))
            was_unit = y.unit
            y.unit = self.unit
            newbs._eigen = newbs._eigen - y._eigen[:, :, :newbs.nbands]
            y.unit = was_unit
        elif isinstance(y, Real):
            if y == 0.0:
                return self
            newbs = deepcopy(self)
            newbs._eigen = newbs._eigen - y
        else:
            raise TypeError("expected BandStructure or float, got {}".format(type(y)))
        # must reset Fermi energy in this case
        newbs._bandedge_calculated = False
        newbs._efermi = None
        return newbs

    # pylint: disable=R0914
    def get_dos(self, emin=None, emax=None, nedos=3000, smearing="Gaussian", sigma=0.05):
        """Generate a DensityOfStates object on a energy grid by smearing the band structure
        with particular smearing scheme

        Args:
            emin, emax (float): the minimum and maximum of energy grid.
                If not specified, the minium and maximum value of the eigenvalues
                will be used, respectively.
            nedos (int): the number of energy grid points
            smearing (str): the smearing scheme
            sigma (float): the width of smearing, in the same unit with BandStructure.

        Returns:
            ``Dos`` object
        """
        from mushroom.core.math_func import Smearing
        from mushroom.core.dos import DensityOfStates

        smearings = {
            "Gaussian": Smearing.gaussian,
        }
        if not isinstance(sigma, Real):
            raise TypeError("sigma must be a real number")
        if smearing not in smearings:
            raise ValueError(
                "smearing type {} is not available".format(smearing))
        sm = smearings[smearing]
        if emin is None:
            emin = np.min(self._eigen)
        if emax is None:
            emax = np.max(self._eigen)
        for e in (emin, emax):
            if not isinstance(e, Real):
                raise TypeError("emin/emax must be a real number")
        # expand the grid to include the smearing width,
        # 10 sigma is sufficient
        sigma = abs(sigma)
        egrid = np.linspace(emin - 10 * sigma, emax + 10 * sigma, nedos)
        tdos = np.zeros((self.nspins, nedos), dtype=self._dtype)
        pdos = None
        if self.has_proj():
            pdos = np.zeros((self.nspins, nedos, self.natoms, self.nprojs), dtype=self._dtype)
        # ? the convolution may be optimized
        for i in range(nedos):
            # shape of d: (nspins, nkpts, nbands)
            d = sm(self._eigen, egrid[i], sigma)
            tdos[:, i] += np.sum(d, axis=(1, 2))
            if self.has_proj():
                p = np.tile(d, (self.natoms, self.nprojs, 1, 1, 1))
                for _j in range(2):
                    p = np.moveaxis(p, 0, -1)
                pdos[:, i, :, :] += np.sum(p * self._pwav, axis=(1, 2))
        return DensityOfStates(egrid, tdos, self._efermi, unit=self.unit,
                               pdos=pdos, atms=self._atms, prjs=self._prjs)


# pylint: disable=R0914
def random_band_structure(nspins: int = 1, nkpts: int = 1, nbands: int = 2,
                          natms: int = 1, nprjs: int = 1,
                          has_proj: bool = False, is_metal: bool = False) -> BandStructure:
    """Return a BandStructure object with fake band energies, occupations and
    projections

    Note:
        For test use only.

    TODO:
        randomize a kpath

    Args:
        nspins, nkpts, nbands, natoms, nprojs (int):
            the dimensions of eigenvalues, occupation numbers and projections.
        has_proj (bool): if fake projection information is generated
        is_metal (bool): if set True, a band structure of metal is generated,
            otherwise semiconductor
    """
    atm_types = ["C", "Si", "Na", "Cl", "P"]
    prj_names = ["s", "px", "py", "pz", "dyz", "dzx", "dxy", "dx2-y2", "dz2"]
    if nkpts < 1:
        nkpts = 1
    # at least one empty band
    if nbands < 2:
        nbands = 2
    if natms < 1:
        natms = 6
    if nprjs < 1:
        nprjs = 1

    shape = (nspins, nkpts, nbands)
    eigen = np.random.random_sample(shape)
    # set vb to the band in the middle
    ivb = int(nbands / 2) - 1
    for i in range(nbands):
        eigen[:, :, i] += i - ivb

    occ = np.zeros(shape)
    occ[:, :, :ivb + 1] = 1.0
    weight = np.random.randint(1, 11, size=nkpts)
    efermi = None
    if is_metal:
        efermi = np.average(eigen[:, :, ivb])
        occ[:, :, ivb] = np.exp(efermi - eigen[:, :, ivb])
        # normalize to 1
        occ[:, :, ivb] /= np.max(occ[:, :, ivb])

    pwav = None
    atms = None
    prjs = None
    if has_proj:
        atms = list(np.random.choice(atm_types, natms))
        prjs = prj_names[:nprjs]
        pwav = np.random.random_sample((*shape, natms, nprjs))
        # normalize
        for ispin in range(nspins):
            for ik in range(nkpts):
                for ib in range(nbands):
                    pwav[ispin, ik, ib, :, :] /= np.sum(pwav[ispin, ik, ib, :, :])
    return BandStructure(eigen, occ, weight=weight, efermi=efermi,
                         pwav=pwav, atms=atms, prjs=prjs)


def split_apb(apb: str):
    """split an atom-projector-band string into lists containing corresponding identifiers

    An atom-projector-bands string is a string with the format as

        atom:projector:bands

    each could be:

        - atom: "S", "Fe", 0, 1, "B,N", "0,1,2"
        - projector: "s", "p,d", "px", "dxy,dz2", 0.
        - band: 0, "vbm", "cbm+1", "0,cbm,vbm-1"

    Returns:
        list, list, list
    """
    if " " in apb:
        raise ValueError("whitespace is not allowed in atom-projector-band string, got", apb)
    try:
        a, p, b = apb.split(":")
    except ValueError as err:
        raise ValueError("should contain two colons") from err

    a, p, b = map(lambda x: split_comma(x, int), [a, p, b])

    return a, p, b


# pylint: disable=C0301
def display_band_analysis(bs: BandStructure, kpts=None, unit="eV", value_only=False, silent=False):
    """display analysis of band structure

    Args:
        bs (BandStructure) : BandStructure object to analyze
        kpts : kpoints list
        value_only (bool) : only show the value of gap, no kpoints or other explanation.
            In this case gaps will be printed in the order of fundamental gap,
            direct gap at VBM and direct gap at CBM
        silent (bool): silent the output.

    Returns:
        string
    """
    if bs.nspins != 1:
        raise NotImplementedError("spin-polarized BS analysis")
    try:
        was_unit = bs.unit
        bs.unit = unit.lower()
        eg_ind = bs.fund_gap()
        direct_gaps = bs.direct_gaps()[0]
        eg_dir = np.min(direct_gaps)
        ik_eg_dir = np.argmin(direct_gaps)
        ivb, ik_vb = bs.ivbm[2], bs.ivbm[1]
        icb, ik_cb = bs.icbm[2], bs.icbm[1]

        slist = []

        def sprint(*args):
            slist.extend(args)

        if not value_only:
            sprint("> band edge between band index {:3d} -> {:3d}".format(ivb, icb))
            if bs.is_gap_direct():
                sprint("> fundamental gap = {:8.4f} {}".format(eg_dir, unit))
                if kpts is None:
                    sprint(">>   ik={:<3d}".format(ik_eg_dir))
                else:
                    sprint(">>   ik={:<3d} ({:7.5f},{:7.5f},{:7.5f})"
                           .format(ik_eg_dir, *kpts[ik_eg_dir, :]))
            else:
                sprint("> fundamental gap = {:8.4f} {}".format(eg_ind, unit))
                if kpts is None:
                    sprint(">> ikvb={:<3d} -> ikcb={:<3d}".format(ik_vb, ik_cb))
                else:
                    sprint(">> ikvb={:<3d} ({:7.5f},{:7.5f},{:7.5f}) -> ikcb={:<3d} ({:7.5f},{:7.5f},{:7.5f})"
                           .format(ik_vb, *kpts[ik_vb, :], ik_cb, *kpts[ik_cb, :]))
                sprint(">> VBM direct gap = {:8.4f} {}".format(direct_gaps[ik_vb], unit))
                sprint(">> CBM direct gap = {:8.4f} {}".format(direct_gaps[ik_cb], unit))
                if kpts is None:
                    sprint("> min. direct gap = {:8.4f} {} at ik={:<3d}"
                           .format(eg_dir, unit, ik_eg_dir))
                else:
                    sprint("> min. direct gap = {:8.4f} {} at ik={:<3d} ({:7.5f},{:7.5f},{:7.5f})"
                           .format(eg_dir, unit, ik_eg_dir, *kpts[ik_eg_dir, :]))
        else:
            if bs.is_gap_direct():
                if kpts is None:
                    sprint("{:8.4f}".format(eg_dir))
                else:
                    sprint("{:8.4f} # ({:f},{:f},{:f})".format(eg_dir, *kpts[ik_eg_dir, :]))
            else:
                if kpts is None:
                    sprint("{:8.4f} {:8.4f} {:8.4f}".format(eg_ind, direct_gaps[ik_vb], direct_gaps[ik_cb]))
                else:
                    sprint("{:8.4f} {:8.4f} {:8.4f} # ({:f},{:f},{:f}) ({:f},{:f},{:f})"
                           .format(eg_ind, direct_gaps[ik_vb], direct_gaps[ik_cb], *kpts[ik_vb], *kpts[ik_cb]))
        bs.unit = was_unit
    except BandStructureError as err:
        raise BandStructureError("fail to display band analysis") from err

    s = "\n".join(slist)
    if not silent:
        print(s)
    return s


def _decode_itrans_string(s):
    """

    Args:
        s (list of str): either "ivk:ick", "ivck:ivb:icb" or "ivk:ick:ivb:icb"
    """
    itrans = [x.strip() for x in s.split(":")]

    def to_int(s, return_s=True):
        try:
            return int(s)
        except ValueError:
            if return_s:
                return s
            return None

    if len(itrans) == 2:
        ivk, ick = list(map(int, itrans))
        ivb = None
        icb = None
    elif len(itrans) == 3:
        ivk = int(itrans[0])
        ick = ivk
        ivb = to_int(itrans[1])
        icb = to_int(itrans[2])
    else:
        ivk, ick = itrans[:2]
        ivk = to_int(ivk, False)
        ick = to_int(ick, False)
        ivb = to_int(itrans[2])
        icb = to_int(itrans[3])
    return ivk, ick, ivb, icb


def display_transition_energies(trans: Sequence[str],
                                bs: BandStructure,
                                kpts=None,
                                unit: str = "eV",
                                value_only: bool = False,
                                silent: bool = False):
    """display the transitions

    Args:
        trans (list of str): either "ivk:ick", "ivck:ivb:icb" or "ivk:ick:ivb:icb"
    """
    if bs.nspins != 1:
        raise NotImplementedError("spin-polarized BS analysis")

    slist = []

    def sprint(*args):
        slist.extend(args)

    try:
        was_unit = bs.unit
        bs.unit = unit.lower()
        if not value_only:
            sprint("> Transition energies ({}):".format(unit))
            sprint(">> {:8s} {:29s}    {:29s}".format("E", "kpt_v", "kpt_c"))
        for t in trans:
            ivk, ick, ivb, icb = _decode_itrans_string(t)
            et, ivk, ick, ivb, icb = bs.get_transition(ivk, ick, ivb=ivb, icb=icb, return_index=True)
            if not value_only:
                if kpts is None:
                    sprint(">> {:8.4f} {:<29d} -> {:<29d}".format(et, ivk, ick))
                else:
                    vk_str = "{:7.4f},{:7.4f},{:7.4f}".format(*kpts[ivk, :])
                    ck_str = "{:7.4f},{:7.4f},{:7.4f}".format(*kpts[ick, :])
                    sprint(">> {:8.4f} {:<3d} ({:s}) -> {:<3d} ({:s})"
                           .format(et, ivk, vk_str, ick, ck_str))
            else:
                if kpts is None:
                    sprint("{:8.4f}".format(et))
                else:
                    vk_str = "{:7.4f},{:7.4f},{:7.4f}".format(*kpts[ivk, :])
                    ck_str = "{:7.4f},{:7.4f},{:7.4f}".format(*kpts[ick, :])
                    sprint("{:8.4f} # ({:s}) ({:s})"
                           .format(et, vk_str, ck_str))
        if value_only and not silent:
            sprint("")
        bs.unit = was_unit
    except BandStructureError as err:
        raise BandStructureError("fail to display transition energies") from err
    s = "\n".join(slist)
    if not silent:
        print(s)
    return s


def resolve_band_crossing(kx, bands, occ=None, pwav=None,
                          deriv_thres: float = None, inplace: bool = False):
    """Resolve the crossing between two bands to make each band smooth.

    Args:
        kx (array-like)
        bands (2-dim ndarray)
        deriv_thres (float)
        occ (2-dim ndarray)
        pwav (4-dim ndarray)
        inplace (bool)

    Returns:
        2-dim ndarray (bands) if occ and pwav are None, otherwise
        2-dim ndarray (bands), 2-dim ndarray (occ) and 4-dim ndarray (pwav).
        None if the corresponding input is None

    Note:
        Side effect: bands and pwav are also changed in place.
    """
    if inplace:
        bands_res = bands
    else:
        bands_res = deepcopy(bands)

    # default value
    if deriv_thres is None:
        deriv_thres = 5.0
    nk = len(kx)
    shape_bands = np.shape(bands_res)
    if len(shape_bands) != 2:
        raise ValueError("bands should be 2-dim, got %d" % len(shape_bands))
    if shape_bands[0] != nk:
        raise ValueError("Inconsistent shape of bands and kx")
    nbands = shape_bands[1]
    if pwav is not None:
        _logger.debug("parsing pwav in band crossing resolution")
        shape_pwav = np.shape(pwav)
        _logger.debug("pwav shape: %r", shape_pwav)
        if len(shape_pwav) < 4 or shape_pwav[0] != nk or shape_pwav[1] != nbands:
            raise ValueError("Invalid shape of pwav, should be 4d: (nk, nbands, :, :)")

    kx = np.array(kx)

    # We scan every 3 points
    derivs_inband = np.zeros((nbands, 2))
    # cross-band derivatives
    permuts = list(permutations(range(nbands), nbands))
    element_permut = tuple(range(nbands))
    del permuts[permuts.index(element_permut)]
    derivs_crossband = np.zeros((len(permuts), nbands, 2))
    bands_adjacent = np.zeros((nbands, 4))

    sumediff_thres = 0.001

    # If there is less than 3 points, we have no idea if we need to resolve.
    # The following loop will not be executed unless there are more than 3 points
    for i in range(1, nk - 1):
        # skip the permutation if i and i+1 are the same kpoint
        # by checking the absolute difference between the band energies
        sumediff = np.sum(np.abs(bands_res[i, :] - bands_res[i + 1, :]))
        if sumediff < sumediff_thres:
            _logger.debug("Current and next k-point the same, sum(ediff) < %f: %d", sumediff_thres, i)
            continue

        # left side
        # find the left non-end-point for point i
        j = max(j for j in range(i - 1, -1, -1) if kx[j] != kx[i])
        kl = kx[j]
        bands_adjacent[:, 0] = bands_res[j, :]
        bands_adjacent[:, 1] = bands_res[j + 1, :]

        # right side
        # find the right non-end-point for point i
        j = min(j for j in range(i + 1, nk) if kx[j] != kx[i])
        kr = kx[j]
        bands_adjacent[:, 2] = bands_res[j - 1, :]
        bands_adjacent[:, 3] = bands_res[j, :]

        # inband derivatives
        derivs_inband[:, 0] = (bands_adjacent[:, 1] - bands_adjacent[:, 0]) / (kx[i] - kl)
        derivs_inband[:, 1] = (bands_adjacent[:, 2] - bands_adjacent[:, 3]) / (kx[i] - kr)
        # crossband derivatives
        for ipermut, permut in enumerate(permuts):
            # left, the same for all
            derivs_crossband[ipermut, :, 0] = (bands_adjacent[:, 1] - bands_adjacent[:, 0]) / (kx[i] - kl)
            # right
            derivs_crossband[ipermut, :, 1] = (bands_adjacent[:, 2] - bands_adjacent[permut, 3]) / (kx[i] - kr)
        diff_derivs_inband = np.sum(np.abs(derivs_inband[:, 1] - derivs_inband[:, 0]))
        diff_derivs_crossband = np.sum(np.abs(derivs_crossband[:, :, 1] - derivs_crossband[:, :, 0]), axis=1)
        arg = np.argmin(diff_derivs_crossband)
        _logger.debug("deriv. diff: inband %f vs min-crossband %f, at %d",
                      diff_derivs_inband, diff_derivs_crossband[arg], i)
        if diff_derivs_inband < diff_derivs_crossband[arg] + deriv_thres:
            continue
        _logger.info("deriv. diff: inband %f >= crossband %f + (%f), possible crossing at %d, switch bands, permut %r",
                     diff_derivs_inband, diff_derivs_crossband[arg], deriv_thres, i, permuts[arg])
        _logger.debug("kx: %f %f %f", kl, kx[i], kr)
        for ib in range(nbands):
            _logger.debug("related %d-th band energies: %r", ib, bands_adjacent[ib, :])
        temp = bands_res[i + 1:, :]
        temp = temp[:, permuts[arg]]
        bands_res[i + 1:, :] = temp[:, :]
        if occ is not None:
            _logger.debug("permuting occ")
            temp = occ[i + 1:, :,]
            temp = temp[:, permuts[arg]]
            occ[i + 1:, :,] = temp[:, :]
        if pwav is not None:
            _logger.debug("permuting pwav")
            temp = pwav[i + 1:, :, :, :]
            temp = temp[:, permuts[arg], :, :]
            pwav[i + 1:, :, :, :] = temp[:, :, :, :]

    _logger.debug("multi-band resolve done")
    # return the disentangled bands
    if occ is None and pwav is None:
        return bands_res
    return bands_res, occ, pwav
