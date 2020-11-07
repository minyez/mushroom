# -*- coding: utf-8 -*-
"""Module that defines class and utilities for band structure
"""
import re
from typing import Sequence, Union

import numpy as np

from mushroom.core.logger import create_logger
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

AtmPrjToken = Union[Key, Sequence[Key]]

_logger = create_logger("bs")
del create_logger

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

    Args:
        eigen (array-like) : the energy (eigenvalues) of all bands to be considered

    Optional args:
        occ (array-like) : the occupation numbers of all bands
        weight (array-like) : the weights of each kpoint, 1-d array,
            either integer weight or scaled weight. default to 1.0
        unit ('ev','ry','au'): the unit of the eigenvalues
        efermi (float): the Fermi level. 
            If not parsed, the valence band maximum will be used.
        keyword argument: wave projection information projection 
            It should have three keys, "atms", "prjs" and "pwav"

    Attributes:
    """
    _dtype = "float64"
    # pylint: disable=R0912,R0915
    def __init__(self, eigen, occ=None, weight=None, unit: str = 'ev', efermi: float = None,
                 pwav=None, atms: Sequence[str] = None, prjs: Sequence[str] = None):
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
        except TypeError:
            _logger.error("failt to convert eigen/weight to ndarray")
            raise BandStructureError

        EnergyUnit.__init__(self, eunit=unit)
        self._emulti = {1: 2, 2: 1}[self._nspins]
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
        if occ is not None:
            self.set_occupations(occ)

        _logger.info("Read bandstructure. Dimensions")
        _logger.info(">> nspins = %d", self._nspins)
        _logger.info(">>  nkpts = %d", self._nkpts)
        _logger.info(">> nbands = %d", self._nbands)

        self._pwav = None
        self._atms = None
        self._prjs = None
        self._natms = 0
        self._nprjs = 0
        if pwav is not None:
            self.parse_proj(pwav=pwav, atms=atms, prjs=prjs)

    def set_occupations(self, occ):
        """set occupation numbers

        Args:
            occ (ndarray): occupation numbers, (nspins, nkpts, nbands)
        """
        if self._occ is not None:
            raise AttributeError("occupations are already set")
        try:
            shape_o = np.shape(occ)
        except ValueError:
            raise ValueError("can not retrive the shape of input occupations")
        shape_e = (self._nspins, self._nkpts, self._nbands)
        if shape_e != shape_o:
            info = "inconsistent eigen/occ shapes: {}, {}".format(shape_e, shape_o)
            _logger.error(info)
            raise BandStructureError
        self._occ = np.array(occ, dtype=self._dtype)
        self._nelect_sp_kp = np.sum(self._occ, axis=2) * self._emulti
        self._nelect_sp = np.dot(self._nelect_sp_kp, self._weight) / np.sum(self._weight)
        self._nelect = np.sum(self._nelect_sp)

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

    def _convert_band_iden(self, band_iden):
        """convert a string of band identifier, like "vbm", "cbm-2", "vbm+3"
        to the correpsonding band index.

        Args:
            band_str (int, str)

        Returns:
            int
        """
        if isinstance(band_iden, int):
            return band_iden
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
        raise ValueError("unrecognized band identifier", band_iden)

    @property
    def unit(self):
        """unit of band energies"""
        return self._eunit

    @unit.setter
    def unit(self, newu: str):
        coef = self._get_eunit_conversion(newu)
        to_conv = [self._eigen,
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
            self._efermi = self.vbm
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
        '''compute the band edges on each spin-kpt channel

        Note:
            When nbands is too small and all bands are found to be valence bands,
            or it is the case for one spin-kpoint channel, the corresponding CB will
            be set to ``np.infty``. 
            Setup of indices of CB remains, thus IndexError might be raised when trying
            get CB value from `icbm` attributes

        Args:
            reload (bool) : redo the calculation of band edges
        '''
        if self._occ is None:
            raise BandStructureError("need occupation number before computing band edges!")
        is_occ = self._occ > THRES_OCC
        vbm = self.__getattribute__("_vbm")
        if vbm is None:
            pass
        else:
            if not reload:
                return

        self._ivbm_sp_kp = np.sum(is_occ, axis=2) - 1
        # when any two indices of ivbm differ, the system is metal
        if np.max(self._ivbm_sp_kp) == np.min(self._ivbm_sp_kp):
            self._is_metal = False
        else:
            self._is_metal = True
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
                        info, i+1, j+1, "CBM for this channel set to infinity")
                    self._cbm_sp_kp[i, j] = np.infty
                else:
                    self._cbm_sp_kp[i, j] = self.eigen[i, j, vb+1]
        self._band_width = np.zeros(
            (self.nspins, self.nbands, 2), dtype=self._dtype)
        self._band_width[:, :, 0] = np.min(self._eigen, axis=1)
        self._band_width[:, :, 1] = np.max(self._eigen, axis=1)
        # VB indices
        self._ivbm_sp = np.array(((0, 0),)*self.nspins)
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
        self._icbm_sp = np.array(((0, 0),)*self.nspins)
        self._cbm_sp = np.min(self._cbm_sp_kp, axis=1)
        self._icbm_sp[:, 0] = np.argmin(self._cbm_sp_kp, axis=1)
        for i in range(self.nspins):
            ik = int(self._icbm_sp[i, 0])
            self._icbm_sp[i, 1] = self._icbm_sp_kp[i, ik]
        self._icbm = np.array((0, 0, 0))
        self._icbm[0] = int(np.argmin(self._cbm_sp))
        self._icbm[1:3] = self._icbm_sp[self._icbm[0], :]
        self._cbm = self._cbm_sp[self._icbm[0]]

    def __lazy_bandedge_return(self, attr: str = None):
        """lazy return of attribute related to band edges

        Args:
            attr (str): name of attribute
        """
        if attr is None:
            self.compute_band_edges()
            return None
        v = self.__getattribute__(attr)
        if v is None:
            self.compute_band_edges()
        v = self.__getattribute__(attr)
        if v is None:
            raise ValueError("attribute {} is not available for band".format(attr.strip("_")))
        return v

    def is_metal(self):
        """bool. True if the bandstructure belongs to a metal, False otherwise
        """
        return self.__lazy_bandedge_return("_is_metal")

    @property
    def ivbm_sp_kp(self):
        """indices of valence band maximum at each spin-kpt channel

        int, shape (nspins, nkpts)
        """
        return self.__lazy_bandedge_return("_ivbm_sp_kp")

    @property
    def icbm_sp_kp(self):
        """indices of conduction band minimum at each spin-kpt channel

        int, shape (nspins, nkpts)
        """
        return self.__lazy_bandedge_return("_icbm_sp_kp")

    @property
    def ivbm_sp(self):
        """indices of valence band maximum per spin

        int, shape (nspins, 2), ikpt, iband
        """
        return self.__lazy_bandedge_return("_ivbm_sp")

    @property
    def icbm_sp(self):
        """indices of conduction band minimum per spin

        int, shape (nspins, 2), ikpt, iband
        """
        return self.__lazy_bandedge_return("_icbm_sp")

    @property
    def ivbm(self):
        """index of valence band maximum

        int, shape (3,), ispin, ikpt, iband
        """
        return self.__lazy_bandedge_return("_ivbm")

    @property
    def icbm(self):
        """index of conduction band minimum

        int, shape (3,), ispin, ikpt, iband
        """
        return self.__lazy_bandedge_return("_icbm")

    @property
    def vbm_sp_kp(self):
        """valiues of valence band maximum at each spin-kpt channel

        float, shape (nspins, nkpts)
        """
        return self.__lazy_bandedge_return("_vbm_sp_kp")

    @property
    def cbm_sp_kp(self):
        """values of conduction band minimum at each spin-kpt channel

        float, shape (nspins, nkpts)
        """
        return self.__lazy_bandedge_return("_cbm_sp_kp")

    @property
    def vbm_sp(self):
        """valiues of valence band maximum per spin

        float, shape (nspins,)
        """
        return self.__lazy_bandedge_return("_vbm_sp")

    @property
    def cbm_sp(self):
        """values of conduction band minimum per spin

        float, shape (nspins,)
        """
        return self.__lazy_bandedge_return("_cbm_sp")

    @property
    def vbm(self):
        """value of valence band maximum

        float
        """
        return self.__lazy_bandedge_return("_vbm")

    @property
    def cbm(self):
        """value of conduction band minimum

        float
        """
        return self.__lazy_bandedge_return("_cbm")

    @property
    def band_width(self):
        """the lower and upper bound of a band

        float, shape (nspins, nbands, 2)
        """
        return self.__lazy_bandedge_return("_band_width")

    def direct_gap(self):
        """Direct gap between VBM and CBM of each spin-kpt channel

        float, shape (nspins, nkpts)
        """
        return self.cbm_sp_kp - self.vbm_sp_kp

    def fund_gap(self):
        """Fundamental gap for each spin channel.

        float, shape (nspins,)
        If it is metal, it is equivalent to the negative value of bandwidth
        of the unfilled band.
        """
        return self.cbm_sp - self.vbm_sp

    def fund_trans(self):
        """Transition responsible for the fundamental gap

        int, shape (nspins, 2)
        """
        vb = np.argmax(self.vbm_sp_kp, axis=1)
        cb = np.argmin(self.vbm_sp_kp, axis=1)
        return tuple(zip(vb, cb))

    def kavg_gap(self):
        """direct band gap averaged over kpoints

        float, shape (nspins,)
        """
        return np.dot(self.direct_gap(), self._weight) / np.sum(self._weight)

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
        except BandStructureError:
            info = "unable to compute effective gap, since no partial wave is parsed. try kavg_gap"
            raise BandStructureError(info)
        if ivb is None or not ivb in range(self.nbands):
            vb_coef = vb_coefs[:, :, np.max(self.ivbm)]
        else:
            vb_coef = vb_coefs[:, :, ivb]
        if icb is None or not icb in range(self.nbands):
            cb_coef = cb_coefs[:, :, np.min(self.icbm)]
        else:
            cb_coef = cb_coefs[:, :, icb]
        # ! abs is added in case ivb and icb are put in the opposite
        inv = np.sum(np.abs(np.reciprocal(self.direct_gap()) * vb_coef * cb_coef))
        if np.allclose(inv, 0.0):
            return np.infty
        return 1.0/inv

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
        if isinstance(ib, Sequence):
            return list(map(self._convert_band_iden, ib))
        return [self._convert_band_iden(ib),]

    def _get_atm_indices(self, atm):
        if self._atms is None:
            if isinstance(atm, int):
                return [atm,]
            if isinstance(atm, Sequence):
                has_str = any(isinstance(a, str) for a in atm)
                if not has_str:
                    return atm
            raise ValueError("parse atms first for atom string")
        return get_str_indices_by_iden(self._atms, atm)

    def _get_prj_indices(self, prj):
        if self._prjs is None:
            if isinstance(prj, int):
                return [prj,]
            if isinstance(prj, Sequence):
                has_str = any(isinstance(p, str) for p in prj)
                if not has_str:
                    return prj
            raise ValueError("parse prjs first for projector string")
        return get_str_indices_by_iden(self._prjs, prj)

    #def get_dos(self, emin=None, emax=None, nedos=3000, smearing="Gaussian", sigma=0.05):
    #    """Generate a Dos object on a energy grid by smearing the band structure
    #    with particular smearing scheme

    #    Args:
    #        emin, emax (float): the minimum and maximum of energy grid.
    #            If not specified, the minium and maximum value of the eigenvalues
    #            will be used, respectively.
    #        nedos (int): the number of energy grid points
    #        smearing (str): the smearing scheme
    #        sigma (float): the width of smearing, in the same unit with BandStructure.

    #    Returns:
    #        ``Dos`` object
    #    """
    #    from mykit.core.dos import Dos
    #    
    #    smearDict = {
    #        "Gaussian": Smearing.gaussian,
    #    }
    #    if not isinstance(sigma, Real):
    #        raise TypeError("sigma must be a real number")
    #    if smearing not in smearDict:
    #        raise ValueError(
    #            "smearing type {} is not available".format(smearing))
    #    sm = smearDict[smearing]
    #    eminAvail, emaxAvail = np.min(self._eigen), np.max(self._eigen)
    #    if emin is None:
    #        emin = eminAvail
    #    if emax is None:
    #        emax = emaxAvail
    #    for e in (emin, emax):
    #        if not isinstance(e, Real):
    #            raise TypeError("emin/emax must be a real number")
    #    if emin < eminAvail:
    #        emin = eminAvail
    #    if emax > emaxAvail:
    #        emax = emaxAvail
    #    # expand the grid a little bit
    #    egrid = np.linspace(emin - abs(emin) * 0.15,
    #                        emax + abs(emax) * 0.15, nedos)
    #    totalDos = np.zeros((nedos, self.nspins), dtype=self._dtype)
    #    if self.has_proj():
    #        projected = {"atoms": self._atms, "projs": self._projs}
    #        pDos = np.zeros((nedos, self.nspins, self.natoms,
    #                         self.nprojs), dtype=self._dtype)
    #        projected["pDos"] = pDos
    #    else:
    #        projected = None
    #    # ? the convolution may be optimized
    #    for i in range(nedos):
    #        # shape of d: (nspins, nkpts, nbands)
    #        d = sm(self._eigen, egrid[i], sigma)
    #        totalDos[i, :] += np.sum(d, axis=(1, 2))
    #        if self.has_proj():
    #            p = np.tile(d, (self.natoms, self.nprojs, 1, 1, 1))
    #            for _j in range(2):
    #                p = np.moveaxis(p, 0, -1)
    #            pDos[i, :, :, :] += np.sum(p * self._pwav, axis=(1, 2))
    #    return Dos(egrid, totalDos, self._efermi, unit=self.unit, projected=projected)


# pylint: disable=R0914
def random_band_structure(nspins: int = 1, nkpts: int = 1, nbands: int = 2,
                          natms: int = 1, nprjs: int = 1,
                          has_proj: bool = False, is_metal: bool = False):
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
    ivb = int(nbands/2) - 1
    for i in range(nbands):
        eigen[:, :, i] += i - ivb

    occ = np.zeros(shape)
    occ[:, :, :ivb+1] = 1.0
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
    except ValueError:
        raise ValueError("should contain two colons")

    a, p, b = map(lambda x: split_comma(x, int), [a, p, b])

    return a, p, b

