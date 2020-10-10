# -*- coding: utf-8 -*-
"""Module that defines class and utilities for band structure
"""
import re
from numbers import Real

import numpy as np

from mushroom._core.logger import create_logger
from mushroom._core.unit import EnergyUnit
from mushroom._core.ioutils import get_str_indices_by_iden

# from mykit.core.visualizer import _BandVisualizer

# eigen, occ (array): shape (nspins, nkpt, nbands)
DIM_EIGEN_OCC = 3
"""int. Required dimension of eigenvalues and occupation numbers
"""

KEYS_BAND_PROJ = ("atoms", "projs", "pwave")
"""tuple. Required keys for wave projection input
"""

BAND_STR_PATTERN = re.compile(r"[vc]bm([-+][\d]+)?")

# DIM_PWAVE = 5
# '''pwave (array): shape (nspins, nkpt, nbands, natoms, nprojs)'''

THRES_EMP = 1.0E-3
THRES_OCC = 1.0 - THRES_EMP

_logger = create_logger(__name__)
del create_logger

class BandStructureError(Exception):
    """exception for band structure"""


class BandStructure(EnergyUnit):
    """Base class for analyzing band structure data.

    The eigenvalues and occupations should be parsed in a shape of 
    (nspins, nkpts, nbands).
    The dimensions are automatically checked.
    Exception will be raised if their shapes are inconsistent.

    Optional keyword arguments, if parsed, should have consistent
    shape with the required arguments.
    They will be ignored if their shapes are inconsistent.

    Args:
        eigen (array-like) : the energy (eigenvalues) of all bands to be considered
        occ (array-like) : the occupation numbers of all bands
        weight (array-like) : the weights of each kpoint, 1-d array,
            either int or float.

    Optional args:
        unit ('ev','ry','au'): the unit of the eigenvalues, in lower case. 
        kvec (array-like): kpoints vectors in reciprocal space (N.B. not the coordinate)
        efermi (float): the Fermi level. 
            If not parsed, the valence band maximum will be used.
        projected (dict) : wave projection information. 
            It should have three keys, "atoms", "projs" and "pwave"

    Attributes:
    """
    _dtype = "float64"

    def __init__(self, eigen, occ, weight=None, unit='ev', efermi=None, projected=None):
        self._nspins, self._nkpts, self._nbands = \
            _check_eigen_occ_weight_consistency(eigen, occ, weight)
        if self._nspins is None:
            info = "Bad eigen, occ and weight shapes: {}, {}, {}".format(
                *map(np.shape, (eigen, occ, weight)))
            raise BandStructureError(info)
        try:
            self._eigen = np.array(eigen, dtype=self._dtype)
            self._occ = np.array(occ, dtype=self._dtype)
            if weight is None:
                weight = np.zeros(self._nkpts)
            self._weight = np.array(weight, dtype=self._dtype)
        except TypeError:
            raise BandStructureError

        EnergyUnit.__init__(self, eunit=unit)
        self._emulti = {1: 2, 2: 1}[self._nspins]
        # channel: ispin, ikpt
        self._nelect_sp_kp = np.sum(self._occ, axis=2) * self._emulti
        # One may parse the kpoints with all zero weight for band calculation
        # In this case, reassign with unit weight
        if np.isclose(np.sum(self._weight), 0.0):
            self._weight[:] = 1.0
        self._nelect_sp = np.dot(
            self._nelect_sp_kp, self._weight) / np.sum(self._weight)
        self._nelect = np.sum(self._nelect_sp)

        self._has_infty_cbm = False
        self._compute_vbm_cbm()
        if efermi is not None:
            assert isinstance(efermi, Real)
            self._efermi = efermi
        else:
            self._efermi = self.vbm

        self._has_proj = False
        self._parse_proj(projected)

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
        if bands:
            b = []
            for ib in bands:
                if isinstance(ib, int):
                    if abs(ib) < self._nbands:
                        b.append(ib)
                elif isinstance(ib, str):
                    i = self._convert_band_str(ib)
                    if i is not None:
                        b.append(i)
        else:
            b = list(range(self._nbands))
        return b

    def _convert_band_str(self, s):
        """convert a string of band identifier, like "vbm", "cbm-2", "vbm+3"
        to the correpsonding band index.

        Args:
            bandStr (str)

        Returns:
            int
        """
        assert isinstance(s, str)
        if BAND_STR_PATTERN.match(s):
            ref = {"v": self.ivbm[-1], "c": self.icbm[-1]}[s[0]]
            if len(s) == 3:
                return ref
            n = int(re.split(r"[-+]", s)[-1])
            if s[3] == '-':
                ib = ref - n
            else:
                ib = ref + n
            # check if the band index is valid
            if 0 <= ib < self.nbands:
                return ib
        return None

    @property
    def unit(self):
        """unit of band energies"""
        return self._eunit

    @unit.setter
    def unit(self, newu):
        coef = self._get_eunit_conversion(newu)
        toConv = [self._eigen, self._bandWidth,
                  self._vbm_sp, self._vbm_sp_kp,
                  self._cbm_sp, self._cbm_sp_kp,
                  ]
        if coef != 1:
            self._efermi *= coef
            self._vbm *= coef
            self._cbm *= coef
            for item in toConv:
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
        '''float. The energy of Fermi level.'''
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

    def _parse_proj(self, projected):
        """Parse the partial wave information
        """
        if not projected is None:
            try:
                self._atms, self._projs, pwave = \
                    self._check_project_consistency(projected)
                self._pwave = np.array(pwave, dtype=self._dtype)
                self._has_proj = True
            except ValueError:
                _logger.warning("Bad projection input. Skip.")

    @property
    def has_proj(self):
        '''Bool'''
        return self._has_proj

    @property
    def atms(self):
        '''list of strings, types of each atom. 

        Returns:
            list of str, atomic symbols
            None if no projection information was parsed
        '''
        if self._has_proj:
            return self._atms
        return None

    @property
    def natoms(self):
        """number of atoms"""
        try:
            return len(self.atms)
        except TypeError:
            return 0

    @property
    def projs(self):
        '''list of strings, names of atomic projectors

        None if no projection information was parsed
        '''
        if self.has_proj:
            return self._projs
        return None

    @property
    def nprojs(self):
        """number of projectors"""
        try:
            return len(self.projs)
        except TypeError:
            return 0

    @property
    def pwave(self):
        '''Array, partial waves for each projector on each atom.

        shape (nspins, nkpts, nbands, natoms, nprojs)

        None if no projection information was parsed.
        '''
        if self.has_proj:
            return self._pwave
        return None

    def _compute_vbm_cbm(self):
        '''compute the band edges on each spin-kpt channel

        Note:
            When nbands is too small and all bands are found to be valence bands,
            or it is the case for one spin-kpoint channel, the corresponding CB will
            be set to ``np.infty``. 
            Setup of indices of CB remains, thus IndexError might be raised when trying
            get CB value from `icbm` attributes
        '''
        is_occ = self._occ > THRES_OCC

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
        self._bandWidth = np.zeros(
            (self.nspins, self.nbands, 2), dtype=self._dtype)
        self._bandWidth[:, :, 0] = np.min(self._eigen, axis=1)
        self._bandWidth[:, :, 1] = np.max(self._eigen, axis=1)
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

    @property
    def is_metal(self):
        '''bool.

        True if the bandstructure belongs to a metal, False otherwise
        '''
        return self._is_metal

    @property
    def ivbm_sp_kp(self):
        '''indices of valence band maximum at each spin-kpt channel

        int, shape (nspins, nkpts)
        '''
        return self._ivbm_sp_kp

    @property
    def icbm_sp_kp(self):
        '''indices of conduction band minimum at each spin-kpt channel

        int, shape (nspins, nkpts)
        '''
        return self._icbm_sp_kp

    @property
    def ivbm_sp(self):
        '''indices of valence band maximum per spin

        int, shape (nspins, 2), ikpt, iband
        '''
        return self._ivbm_sp

    @property
    def icbm_sp(self):
        '''indices of conduction band minimum per spin

        int, shape (nspins, 2), ikpt, iband
        '''
        return self._icbm_sp

    @property
    def ivbm(self):
        '''index of valence band maximum

        int, shape (3,), ispin, ikpt, iband
        '''
        return self._ivbm

    @property
    def icbm(self):
        '''index of conduction band minimum

        int, shape (3,), ispin, ikpt, iband
        '''
        return self._icbm

    @property
    def vbm_sp_kp(self):
        '''valiues of valence band maximum at each spin-kpt channel

        float, shape (nspins, nkpts)
        '''
        return self._vbm_sp_kp

    @property
    def cbm_sp_kp(self):
        '''values of conduction band minimum at each spin-kpt channel

        float, shape (nspins, nkpts)
        '''
        return self._cbm_sp_kp

    @property
    def vbm_sp(self):
        '''valiues of valence band maximum per spin

        float, shape (nspins,)
        '''
        return self._vbm_sp

    @property
    def cbm_sp(self):
        """values of conduction band minimum per spin

        float, shape (nspins,)
        """
        return self._cbm_sp

    @property
    def vbm(self):
        """value of valence band maximum

        float
        """
        return self._vbm

    @property
    def cbm(self):
        '''value of conduction band minimum

        float
        '''
        return self._cbm

    @property
    def bandWidth(self):
        '''the lower and upper bound of a band

        float, shape (nspins, nbands, 2)
        '''
        return self._bandWidth

    @property
    def direct_gap(self):
        '''Direct gap between VBM and CBM of each spin-kpt channel

        float, shape (nspins, nkpts)
        '''
        return self._cbm_sp_kp - self._vbm_sp_kp

    @property
    def fund_gap(self):
        '''Fundamental gap for each spin channel.

        float, shape (nspins,)
        If it is metal, it is equivalent to the negative value of bandwidth
        of the unfilled band.
        '''
        return self._cbm_sp - self._vbm_sp

    @property
    def fund_trans(self):
        '''Transition responsible for the fundamental gap

        int, shape (nspins, 2)
        '''
        vb = np.argmax(self._vbm_sp_kp, axis=1)
        cb = np.argmin(self._vbm_sp_kp, axis=1)
        return tuple(zip(vb, cb))

    @property
    def kavg_gap(self):
        '''direct band gap averaged over kpoints

        float, shape (nspins,)
        '''
        return np.dot(self.direct_gap, self._weight) / np.sum(self._weight)

    def _check_project_consistency(self, projected):
        try:
            assert isinstance(projected, dict)
        except AssertionError:
            return (None, None, None)
        try:
            for key in KEYS_BAND_PROJ:
                assert key in projected
        except AssertionError:
            return (None, None, None)
        # print(projected)
        atoms = projected["atoms"]
        projs = projected["projs"]
        pwave = projected["pwave"]
        try:
            natoms = len(atoms)
            nprojs = len(projs)
            _logger.info("Shapes: %r %r", np.shape(pwave),
                              (self._nspins, self._nkpts,
                               self._nbands, natoms, nprojs),
                             )
            assert np.shape(pwave) == \
                (self._nspins, self._nkpts, self._nbands, natoms, nprojs)
        except (AssertionError, TypeError):
            return (None, None, None)
        return atoms, projs, pwave

    # * Projection related functions
    def effective_gap(self, ivb=None, atom_vbm=None, proj_vbm=None,
                      icb=None, atom_cbm=None, proj_cbm=None):
        '''Compute the effective band gap between ``ivb`` and ``icb``, 
        the responsible transition of which associates projector `proj_vbm` on `atom_vbm` in VB
        and `proj_cbm` on atom `atom_cbm` in CB.

        If no projection information was parsed, the inverse of the k-averaged gap inverse
        will be returned.

        Args:
            ivb (int): index of the lower band. Use VBM if not specified or is invalid index.
            icb (int): index of the upper band. Use CBM if not specified or is invalid index.
            atom_vbm (int, str, Iterable): atom where the VB projector is located
            atom_cbm (int, str, Iterable): atom where the CB projector is located
            proj_vbm (int, str, Iterable): index of VB projector
            proj_cbm (int, str, Iterable): index of CB projector

        Note:
            Spin-polarization is not considered in retriving projection coefficients.
        '''
        vb_coefs = self.sum_atom_proj_comp(atom_vbm, proj_vbm, fail_one=True)
        cb_coefs = self.sum_atom_proj_comp(atom_cbm, proj_cbm, fail_one=True)
        if ivb is None or not ivb in range(self.nbands):
            vb_coef = vb_coefs[:, :, np.max(self.ivbm)]
        else:
            vb_coef = vb_coefs[:, :, ivb]
        if icb is None or not icb in range(self.nbands):
            cb_coef = cb_coefs[:, :, np.min(self.icbm)]
        else:
            cb_coef = cb_coefs[:, :, icb]
        # ! abs is added in case ivb and icb are put in the opposite
        inv = np.sum(np.abs(np.reciprocal(self.direct_gap) * vb_coef * cb_coef))
        if np.allclose(inv, 0.0):
            return np.infty
        return 1.0/inv

    def sum_atom_proj_comp(self, atom=None, proj=None, fail_one=True):
        """Sum the partial wave for projectors `proj` on atoms `atom`

        Args:
            atom (int, str, Iterable)
            proj (int, str, Iterable)
            fail_one (bool): control the return when no projection is available. 
                if set True, return np.ones with correct shape, otherwise np.zeros

        Returns:
            (nspins, nkpts, nbands)
        """
        if not self.has_proj:
            func = {True: np.ones, False: np.zeros}
            try:
                return func[fail_one]((self.nspins, self.nkpts, self.nbands))
            except KeyError:
                raise TypeError("fail_one should be bool type.")
        if atom is None:
            at_ids = list(range(self.natoms))
        else:
            at_ids = self._get_atom_indices(atom)
        if proj is None:
            pr_ids = list(range(self.nprojs))
        else:
            pr_ids = self._get_proj_indices(proj)
        coeff = np.zeros((self.nspins, self.nkpts, self.nbands))
        for a in at_ids:
            for p in pr_ids:
                coeff += self.pwave[:, :, :, a, p]
        return coeff

    def _get_atom_indices(self, atom):
        if self.has_proj:
            return get_str_indices_by_iden(self._atms, atom)
        return []

    def _get_proj_indices(self, proj):
        if self.has_proj:
            return get_str_indices_by_iden(self._projs, proj)
        return []

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
    #    if self.has_proj:
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
    #        if self.has_proj:
    #            p = np.tile(d, (self.natoms, self.nprojs, 1, 1, 1))
    #            for _j in range(2):
    #                p = np.moveaxis(p, 0, -1)
    #            pDos[i, :, :, :] += np.sum(p * self._pwave, axis=(1, 2))
    #    return Dos(egrid, totalDos, self._efermi, unit=self.unit, projected=projected)


def _check_eigen_occ_weight_consistency(eigen, occ, weight=None):
    """Check if eigenvalues, occupation number and kweights data have the correct shape

    Returns:
        tuple, the shape of eigen/occ when the shapes of input are consistent,
            empty tuple otherwise.
    """
    shapee = np.shape(eigen)
    shapeo = np.shape(occ)
    consist = [len(shapee) == DIM_EIGEN_OCC,
               shapee == shapeo,]
    # if weight is manually parsed
    if weight is not None:
        shapew = np.shape(weight)
        consist.extend([len(shapew) == 1,
                        shapew[0] == shapee[1]])
    if all(consist):
        return shapee
    return (None,) * DIM_EIGEN_OCC


def random_band_structure(nspins=1, nkpts=1, nbands=2, natoms=1, nprojs=1,
                          has_proj=False, is_metal=False):
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
        otherwise that of semiconductor
    """
    atom_types = ["C", "Si", "Na", "Cl", "P"]
    proj_names = ["s", "px", "py", "pz", "dyz", "dzx", "dxy", "dx2-y2", "dz2"]
    if nkpts < 1:
        nkpts = 1
    # at least one empty band
    if nbands < 2:
        nbands = 2
    if natoms < 1:
        natoms = 6
    if nprojs < 1:
        nprojs = 1

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
    projected = None
    if has_proj:
        atoms = list(np.random.choice(atom_types, natoms))
        projs = proj_names[:nprojs]
        pwave = np.random.random_sample((*shape, natoms, nprojs))
        # normalize
        for ispin in range(nspins):
            for ik in range(nkpts):
                for ib in range(nbands):
                    pwave[ispin, ik, ib, :,
                          :] /= np.sum(pwave[ispin, ik, ib, :, :])
                    projected = {
                        "atoms": atoms,
                        "projs": projs,
                        "pwave": pwave,
                        }
    return BandStructure(eigen, occ, weight=weight, efermi=efermi, projected=projected)

