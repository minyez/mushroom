# -*- coding: utf-8 -*-
"""utilities of vasp"""
import os
import struct
from io import StringIO
from copy import deepcopy
from itertools import product
from typing import Tuple, List, Union
import pathlib

import numpy as np
try:
    from bs4 import BeautifulSoup as BS
except ImportError:
    BS = None

from mushroom.core.logger import loggers
from mushroom.core.ioutils import conv_string, raise_no_module, open_textio
from mushroom.core.dos import DensityOfStates
from mushroom.core.bs import BandStructure
from mushroom.core.pw import PWBasis
from mushroom.core.cell import Cell, latt_equal
from mushroom.core.typehint import Path

_logger = loggers["vasp"]

__all__ = [
    "read_eigen",
    "read_procar",
    "read_doscar",
    "read_poscar",
    "read_xml",
]


# pylint: disable=R0914
def _dict_read_doscar(path: str = "DOSCAR",
                      read_pdos: bool = True, ncl: bool = False) -> dict:
    """read DOSCAR file and returns a dict

    Args:
        path (str) : path to DOSCAR file. default to "DOSCAR"
        read_pdos (bool) : if read projected densit of states
        ncl (bool) : DOS file from non-collinear calculation

    Returns:
        dict

    TODO:
        - automatic ncl check
    """
    def __read_splitted_atom_data(dls, nspins):
        data = np.array([x[1:] for x in dls])
        nedos = len(dls)
        nprjs = len(data[0]) // nspins
        # reshape to (nspins, nedos, nprjs)
        # first convert to (nedos, nspins, nprjs), then switch the first two axis
        return data.reshape((nedos, nspins, nprjs), order='F').swapaxes(0, 1)

    _logger.info("Reading DOSCAR from %s", os.path.realpath(path))
    with open(path, 'r') as h:
        lines = [l.split() for l in h.readlines()]
    natms = int(lines[0][0])
    nedos, efermi = map(float, lines[5][2:4])
    nedos = int(nedos)
    if len(lines[6]) == 3:
        nspins = 1
    else:
        nspins = 2
    if ncl:
        raise NotImplementedError
    _logger.info(">> ISPIN = %d", nspins)
    _logger.info(">> NEDOS = %d", nedos)

    egrid = np.array([x[0] for x in lines[6:6 + nedos]])
    # total density of states
    tdos = [x[1:1 + nspins] for x in lines[6:6 + nedos]]
    tdos = np.array(tdos).transpose()
    pdos = None
    if read_pdos and len(lines) > nedos + 7:
        nprjs = (len(lines[nedos + 7]) - 1) // nspins
        pdos = np.zeros((nspins, nedos, natms, nprjs))
        for ia in range(natms):
            start = (ia + 1) * (nedos + 1) + 6
            pdos[:, :, ia, :] = __read_splitted_atom_data(lines[start:start + nedos], nspins=nspins)

    return {"egrid": egrid,
            "tdos": tdos,
            "efermi": efermi,
            "pdos": pdos,
            }


def read_doscar(path: str = "DOSCAR", read_pdos: bool = True,
                reset_fermi: bool = False, ncl: bool = False) -> DensityOfStates:
    """read DOSCAR file and returns a DensityOfStates object

    Args:
        path (str) : path to DOSCAR file. default to "DOSCAR"
        read_pdos (bool) : if read projected densit of states
        reset_fermi (bool) : unset Fermi energy obtained from DOSCAR
            this is useful when one wants a dos with it VBM as energy zero
        ncl (bool) : DOS file from non-collinear calculation

    Returns:
        a DensityOfStates object
    """
    d = _dict_read_doscar(path=path, ncl=ncl, read_pdos=read_pdos)
    if reset_fermi:
        d["efermi"] = None
    return DensityOfStates(**d, unit='ev')


# pylint: disable=R0914
def _dict_read_procar(path: str = "PROCAR") -> dict:
    """read PROCAR file

    Args:
        path (str) : path to PROCAR file. default to "PROCAR"
    """
    def __read_band_data(dls):
        """Read data from datalines in the form

        band n # energy x.xxxx # occ. x.xxxxxx

        ion s py pz ....
        1 0.0 0.0 0.0 ...
        2 0.0 0.0 0.0 ...
        """
        eo = dls[0].split()
        e, o = map(float, (eo[-4], eo[-1]))
        s = [" ".join(x.split()[1:-1]) for x in dls[3:]]
        return e, o, np.loadtxt(StringIO("\n".join(s)))

    with open(path, 'r') as h:
        lines = h.readlines()[1:]
    l = lines[0].split()
    nkpts, nbands, natms = map(int, [l[3], l[7], l[-1]])
    nspins = 1
    # extra line "tot" for more than 1 atom
    has_tot_line = int(natms > 1)
    # remove the ion index and tot
    prjs = lines[7].split()[1:-1]
    nprjs = len(prjs)
    kpt_span = nbands * (natms + 4 + has_tot_line) + 3
    if len(lines) > (1 + nkpts * kpt_span):
        nspins = 2
    eigen = np.zeros((nspins, nkpts, nbands))
    occ = np.zeros((nspins, nkpts, nbands))
    kptw = np.zeros((nkpts, 4))
    pwav = np.zeros((nspins, nkpts, nbands, natms, nprjs))
    for ispin in range(nspins):
        for ikpt in range(nkpts):
            kptw[ikpt, :] = np.array(conv_string(lines[ikpt * kpt_span + 2], float, 3, 4, 5, -1))
            for ib in range(nbands):
                # the line index with prefix band
                start = ispin * (1 + nkpts * kpt_span) + \
                    1 + ikpt * kpt_span + ib * (natms + 4 + has_tot_line) + 3
                eigen[ispin, ikpt, ib], occ[ispin, ikpt, ib], pwav[ispin, ikpt, ib, :, :] \
                    = __read_band_data(lines[start:start + natms + 3])
    return {
        "eigen": eigen,
        "occ": occ,
        "weight": kptw[:, 3],
        "kpoints": kptw[:, :3],
        "pwav": pwav,
        "prjs": prjs,
    }


# pylint: disable=R0914
def read_procar(path: str = "PROCAR", filter_k_before: int = 0,
                filter_k_behind: int = None) -> Tuple[BandStructure, np.ndarray]:
    """read PROCAR and return a BandStructure object

    Args:
        path (str) : path to the PROCAR file
        filter_k_before (int)
        filter_k_behind (int)
    """
    d = _dict_read_procar(path=path)
    eigen, occ, weight, kpoints, pwav, prjs = \
        map(d.get, ["eigen", "occ", "weight", "kpoints", "pwav", "prjs"])
    if filter_k_behind is None:
        filter_k_behind = len(kpoints)
    eigen = eigen[:, filter_k_before:filter_k_behind, :]
    occ = occ[:, filter_k_before:filter_k_behind, :]
    weight = weight[filter_k_before:filter_k_behind]
    kpoints = kpoints[filter_k_before:filter_k_behind, :]
    pwav = pwav[:, filter_k_before:filter_k_behind, :, :, :]
    return BandStructure(eigen, occ, weight, unit='ev', pwav=pwav, prjs=prjs), kpoints


def read_xml(*datakey, path: str = "vasprun.xml") -> dict:
    """read vasprun.xml to extract data.

    The reason to use positional arguments to specify the data to extract
    is to avoid processing uncessary data for large XML file.

    Args:
        path (str) : path to the vasp xml file. Default to vasprun.xml
        arguments: key/identifier of data to extract.
            Currently supported:
                kpoints: kpoints in reciprocal vector coordinates
    Returns:
        dict
    """
    raise_no_module(BS, "BeautifulSoup", "reading vasprun.xml")
    objects = {}
    avail_keys = {
        "kpoints": __read_xml_kpoints,
    }
    if not datakey:
        _logger.warning("no identifier specified in XML")
        return objects
    with open(path, 'rb') as h:
        xml = BS(h.read(), 'xml')
    for key in datakey:
        try:
            objects[key] = avail_keys.get(key)(xml)
        except KeyError as err:
            raise ValueError("datakey {} is not supported for vasp xml parser".format(key)) from err
    return objects


def __read_xml_dos(xml: BS):
    """get the density of states from xml"""


def __read_xml_kpoints(xml: BS):
    """get the kpoints from xml"""
    kpts = "".join(k.string for k in xml.find(name="varray", attrs={"name": "kpointlist"}))
    kpts = np.loadtxt(StringIO(kpts))
    return kpts


def _dict_read_eigen(path="EIGENVAL") -> dict:
    """read band structure from EIGENVAL

    Args:
        path (str) : path to EIGENVAL

    Note:
        The occupation number in vasp eigenvalue file is not always the true number.
        For spin-unpolarized calculations (ISPIN=1), you need to multiply it by 2.

    Returns:
        dict
    """
    def __read_kpt_data(dls, nspins):
        # remove band index
        s = StringIO("\n".join(" ".join(x.split()[1:]) for x in dls))
        data = np.loadtxt(s).transpose()
        return data[:nspins, :], data[nspins:, :]

    with open(path, 'r') as h:
        lines = h.readlines()
    natms, _, _, nspins = map(int, lines[0].split())
    nelect, nkpts, nbands = map(int, lines[5].split())
    nelect = float(nelect)
    del lines[:6]
    # now the first line is an empty line before the first kpoint
    eigen = np.zeros((nspins, nkpts, nbands))
    occ = np.zeros((nspins, nkpts, nbands))
    kptw = np.zeros((nkpts, 4))

    for ik in range(nkpts):
        start = ik * (nbands + 2) + 1
        kptw[ik, :] = np.array(lines[start].split())
        eigen[:, ik, :], occ[:, ik, :] = \
            __read_kpt_data(lines[start + 1:start + 1 + nbands], nspins=nspins)
    if nspins == 1:
        occ *= 2.0
    d = {
        "eigen": eigen,
        "occ": occ,
        "weight": kptw[:, 3],
        "kpoints": kptw[:, :3],
        "natms": natms,
    }
    return d


def read_eigen(path: str = "EIGENVAL", filter_k_before: int = 0, filter_k_behind: int = None):
    """read band structure from EIGENVAL

    Args:
        path (str) : path to EIGENVAL
        filter_k_before (int)
        filter_k_behind (int)

    Returns:
        BandStructure, int, 2d-array
    """
    d = _dict_read_eigen(path=path)
    eigen, occ, weight, kpoints, natms = \
        map(d.get, ["eigen", "occ", "weight", "kpoints", "natms"])
    if filter_k_behind is None:
        filter_k_behind = len(kpoints)
    eigen = eigen[:, filter_k_before:filter_k_behind, :]
    occ = occ[:, filter_k_before:filter_k_behind, :]
    weight = weight[filter_k_before:filter_k_behind]
    kpoints = kpoints[filter_k_before:filter_k_behind, :]
    return BandStructure(eigen, occ, weight), natms, kpoints


read_poscar = Cell.read_vasp


class WaveCar:
    """object to read Wavecar

    dtype different from complex64 is not tested

    For system with inversion symmetry, when symmetry is switched on (ISYM>0),
    VASP seems to use C_{-G} = C^*_{G} to reduce the size of coefficients.
    """
    known_nprec = {
        45200: ('complex64', 16, False),
        # 45210: ('complex128', 32, False),
        # 53300: ('complex64', 16, True),
        # 53310: ('complex128', 32, True),
    }

    def __init__(self, pwavecar: Path):
        _logger.info("reading wavecar: %s", str(pwavecar))
        with open(pwavecar, 'rb') as h:
            _recl, nspins, nprec = struct.unpack('ddd', h.read(24))
            nprec = int(nprec)
            if nprec not in WaveCar.known_nprec:
                msg = "precision ({}) is not supported".format(nprec)
                raise ValueError(msg)
        self._nprec = nprec
        self._dtype, self.width, self._is_symmetrized = WaveCar.known_nprec[nprec]
        self.pwavecar = pwavecar
        self._fhandle = None
        self._recl = int(_recl)
        self._nspins = int(nspins)
        # 12 double: nkpts, nbands, encut, latt 3x3
        with open(self.pwavecar, 'rb') as h:
            h.seek(self._recl)
            data = struct.unpack('d' * 12, h.read(96))
            self._nkpts, self._nbands = map(int, data[:2])
            self._encut = data[2]
            self.latt = np.array(data[3:]).reshape((3, 3))
        self._pw = PWBasis(self._encut, self.latt, eunit="ev", lunit="ang", order_kind="vasp")
        _logger.debug(">> record length = %d", self._recl)
        _logger.debug(">> coeff.'s type = %s", self._dtype)
        _logger.debug(">> use symmetry? = %s", self._is_symmetrized)
        _logger.debug(">> nspins = %d", self._nspins)
        _logger.debug(">>  nkpts = %d", self._nkpts)
        _logger.debug(">> nbands = %d", self._nbands)
        _logger.debug(">>  encut = %f", self._encut)
        # each kpt block has an extra line to store the information
        self._blk_ikpt = self._nbands + 1
        # an extra line at the end for nprec=533xx
        if self._is_symmetrized:
            self._blk_ikpt += 1
        self._blk_ispin = self._nkpts * self._blk_ikpt
        self._bs = None
        self._kpts = None
        self._nplanes = None
        self._coeffs = {}

    @property
    def recl(self):
        """record length"""
        return self._recl

    @property
    def nprec(self):
        """precision token"""
        return self._nprec

    @property
    def dtype(self):
        """data type"""
        return self._dtype

    @property
    def nbands(self):
        """number of bands"""
        return self._nbands

    @property
    def encut(self):
        """cut off"""
        return self._encut

    @property
    def nspins(self):
        """number of spin channels"""
        return self._nspins

    @property
    def nkpts(self):
        """number of k-points"""
        return self._nkpts

    @property
    def is_symmetrized(self):
        """if the system is symmetrized"""
        return self._is_symmetrized

    def _compute_kpts_bs_nplanes(self):
        kpts = []
        eigen = []
        occ = []
        nplanes = []

        interval = 2
        if self._is_symmetrized:
            interval = 3
        n = self._nbands * interval + 4
        with open(self.pwavecar, 'rb') as h:
            for ispin, ikpt in product(*map(range, [self._nspins, self._nkpts])):
                h.seek(self._seek_record(ispin, ikpt, iband=-1))
                data = struct.unpack('d' * n, h.read(8 * n))
                nplanes.append(int(data[0]))
                kpts.append(data[1:4])
                eigen.extend(data[4::interval])
                occ.extend(data[3 + interval::interval])
        eigen = np.array(eigen).reshape(
            (self._nspins, self._nkpts, self._nbands))
        occ = np.array(occ).reshape((self._nspins, self._nkpts, self._nbands))
        nplanes = np.array(nplanes).reshape((self._nspins, self._nkpts))
        self._bs = BandStructure(eigen, occ)
        self._kpts = np.array(kpts)
        self._nplanes = nplanes

    @property
    def bs(self):
        """band structure"""
        if self._bs is None:
            self._compute_kpts_bs_nplanes()
        return self._bs

    @property
    def kpts(self):
        """band structure"""
        if self._kpts is None:
            self._compute_kpts_bs_nplanes()
        return self._kpts

    @property
    def nplanes(self):
        """band structure"""
        if self._nplanes is None:
            self._compute_kpts_bs_nplanes()
        return self._nplanes

    def get_raw_coeff(self, ispin: int, ikpt: int, iband: int, cache=True):
        """get the raw plane-wave coefficient of band state

        Args:
            ispin, ikpt, iband (int): the spin, kpoint and band index of a particular band
            cache (bool): use cached data
        """
        coef = self._coeffs.get((ispin, ikpt, iband), None)
        if coef is not None and cache:
            return coef
        if self._fhandle is None:
            self._fhandle = open(self.pwavecar, 'rb')
        self._fhandle.seek(self._seek_record(ispin, ikpt, iband))
        nplane = self.nplanes[ispin, ikpt]
        data = self._fhandle.read(nplane * self.width)
        coef = np.frombuffer(data, dtype=self._dtype, count=nplane)
        if cache:
            self._coeffs[(ispin, ikpt, iband)] = coef
        return coef

    def get_ipw(self, ikpt: int):
        """get the integer planewave index at kpoint ``ikpt``

        Args:
            ikpt (int)

        Returns:
            list
            tuple
        """
        return self._pw.get_ipw(self.kpts[ikpt], symmetrize=self.is_symmetrized)

    def export_cube(self, ispin: int, ikpt: int, iband: int):
        """export the wavefunction at k-point ``ikpt`` and band ``iband``
        """
        raise NotImplementedError

    def close(self):
        """close the binary handle"""
        if self._fhandle is not None:
            self._fhandle.close()
            self._fhandle = None

    def _seek_record(self, ispin: int, ikpt: int, iband: int):
        """seek to the record for the coefficients at ispin, ikpt, iband

        Args:
            ispin, ikpt, iband (int): the spin, kpoint and band index of a particular band
                Particularly, set iband to -1 to reach the information line of each kpoint.
        """
        # here 1 stands for the information line of each kpt
        index = self._blk_ispin * ispin + self._blk_ikpt * ikpt + iband + 1
        # here 2 stands for the first two lines of size and lattice information
        return (index + 2) * self._recl


class ChgLike:
    """object to represent a charge distribution computed from vasp.

    In these files, the charge data are recorded in F order, i.e. x fastest.
    """

    def __init__(self, cell: Cell, rawdata):
        self._cell = cell
        self.shape = np.shape(rawdata)
        self.size = np.prod(self.shape)
        self.rawdata = rawdata

    @property
    def natm(self):
        """number of atoms"""
        return self._cell.natm

    def _add_or_sub(self, chglike, operation="add"):
        if self.shape != chglike.shape:
            raise TypeError("data shape are different")
        if latt_equal(self._cell, chglike._cell):
            _logger.warning("charges with different lattice!")
        if operation == "add":
            new = self.rawdata + chglike.rawdata
        if operation == "sub":
            new = self.rawdata - chglike.rawdata
        return type(self)(self._cell, new)

    def __add__(self, chglike):
        return self._add_or_sub(chglike, "add")

    def __sub__(self, chglike):
        return self._add_or_sub(chglike, "sub")

    def export_cube(self):
        """export the charge distribution data as cube file

        Returns:
            str
        """
        from mushroom.visual.cube import Cube

        was_d = self._cell.coord_sys == "D"
        if was_d:
            self._cell.coord_sys = "C"
        voxel_vecs = self._cell.latt.transpose() / self.shape
        voxel_vecs = voxel_vecs.transpose()
        data = self.rawdata / self._cell.vol
        # divide the cell volume from the raw data
        cube = Cube(data,
                    voxel_vecs=voxel_vecs,
                    atms=self._cell.atms,
                    posi=self._cell.posi,
                    origin=[0., 0., 0.], unit="ang",
                    )
        if was_d:
            self._cell.coord_sys = "D"
        return cube.export()


def read_chg(pchg: Path):
    """read a CHG/CHGCAR file and return a ChgLike object"""
    pchg = pathlib.Path(pchg)
    with pchg.open('r') as h:
        cell_lines = []
        while True:
            l = h.readline()
            if not l.strip():
                break
            cell_lines.append(l)
        cell = read_poscar(StringIO("".join(cell_lines)))
        cell.unit = "ang"
        shape = tuple(map(int, h.readline().split()))
        lines = h.readlines()
        # check columns, since CHG has 10 while CHGCAR has 5
        ncols = len(lines[0].split())
        size = np.prod(shape)
        lines = lines[:size // ncols + 1]
        datastring = StringIO(" ".join(x.strip() for x in lines))
        data = np.loadtxt(datastring)
        rawdata = data.reshape(shape, order='F')
        return ChgLike(cell, rawdata)
    raise IOError("fail to read charge file {}".format(pchg))


class KPoints:
    """handling the KPOINTS file

    Args:
        mode: the mode of KPOINTS file. Available options:
            - "band_recp": band path in unit of reciprocal lattice vector
            - "band_cart": band path in unit of inverse cartisian
            - "A": fully automatic grid (Gamma-centered MP with k-point density)
            - "G": M-P even grids, centered on Gamma
            - "M": M-P even grids, shifted from Gamma
        kpaths: a list of paths in BZ. Each member as a tuple/list, containing
            [coord_start, coord_end, symbol_start, symbol_end].
            coord_start/end are strings, while symbol_start/end can be string or None.
    """
    modes_avail = {
        "band_recp": ["_kpaths", "_ngrids_kpath"],
        "band_cart": ["_kpaths", "_ngrids_kpath"],
        "A": ["_kdense",],
        "G": ["_nkgrids", "_kshifts"],
        "M": ["_nkgrids", "_kshifts"],
        "expl_recp": ["_kpts", "_weights"],
        "expl_cart": ["_kpts", "_weights"],
    }

    def __init__(self, mode: str,
                 nkgrids: Tuple[int] = None,
                 kshifts: Tuple[int] = None,
                 kdense: int = None,
                 kpts: List[Tuple[float]] = None,
                 weights: List[float] = None,
                 kpaths: List[Tuple[str, str, Union[str, None], Union[str, None]]] = None,
                 ngrids_kpath: int = None,
                 comment: str = None):
        self._mode = mode
        self._nkgrids = nkgrids
        self._kshifts = kshifts
        self._kdense = kdense
        self._kpts = kpts
        self._weights = weights
        self._kpaths = kpaths
        self._ngrids_kpath = ngrids_kpath
        self._comment = comment
        self._check_attr_consistency()

    def _check_attr_consistency(self):
        """check the consistency"""
        if self._mode not in self.modes_avail:
            raise ValueError
        for attr in self.modes_avail.get(self._mode):
            if self.__getattribute__(attr) is None:
                raise ValueError("Required attribute {} is not parsed".format(attr[1:]))

    def export(self):
        """export to string"""
        raise NotImplementedError

    @classmethod
    def read(cls, path_kpoints: Union[os.PathLike, str] = "KPOINTS"):
        """read from a KPOINTS file ``path_kpoints``

        Args:
            path_kpoints (path-like)
        """
        with open(path_kpoints, 'r') as h:
            lines = h.readlines()
        if len(lines) < 4:
            raise ValueError("Invalid KPOINTS input, less than 4 lines")

        comment = lines[0].strip()
        ngrids = int(lines[1].split()[0])
        # automatic mode of Monkhorst-Pack grid
        if ngrids == 0:
            mode = lines[2][0].upper()
            nkgrids = None
            kshifts = None
            kdense = None
            if mode in ["G", "M"]:
                nkgrids = list(map(int, lines[3].split()))
                kshifts = list(map(int, lines[4].split()))
            elif mode == "A":
                kdense = int(lines[3].strip())
            else:
                raise ValueError("Unknown mode {} from input {}".format(mode, path_kpoints))
            return cls(mode, nkgrids=nkgrids, kshifts=kshifts, kdense=kdense, comment=comment)

        l2 = lines[2].strip().lower()

        # line mode
        if l2.startswith("l"):  # "line"
            if lines[3].strip().lower().startswith("r"):  # "rec"
                mode = "band_recp"
            elif lines[3].strip().lower().startswith("c"):  # "rec"
                mode = "band_cart"
            else:
                raise ValueError("line mode not supported: {}".format(path_kpoints))
            lines = lines[4:]
            kpaths = []
            for l in lines:
                if l.strip() == "":
                    continue
                kpt = l.replace("!", "").split()
                if len(kpt) == 3:
                    kpaths.append([" ".join(kpt), None])
                elif len(kpt) == 4:
                    kpaths.append([" ".join(kpt[:3]), kpt[3]])
                else:
                    raise ValueError("Invalid kpoint end: {}".format(l))
            # check odd number of end points
            if len(kpaths) % 2 == 1:
                raise ValueError("Odd number of kpoint ends, check input: {}".format(path_kpoints))
            kpaths = [[
                kpaths[i][0], kpaths[i + 1][0], kpaths[i][1], kpaths[i + 1][1]
            ] for i in range(0, len(kpaths), 2)]
            return cls(mode, kpaths=kpaths, ngrids_kpath=ngrids, comment=comment)

        # explicit mode
        if l2.startswith("c") or l2.startswith("k"):  # Cartisian
            mode = "expl_cart"
        else:
            mode = "expl_recp"
        lines = lines[3:]
        if len(lines) < ngrids:
            raise ValueError("number of k-points in lines is inconsistent with the header")
        kpts = []
        weights = []
        for i in range(ngrids):
            words = lines[i].split()
            try:
                k1, k2, k3, weight = map(float, words)
                kpts.append([k1, k2, k3])
                weights.append(weight)
            except ValueError as e:
                raise ValueError("fail to convert line {} to kpoint and weight".format(i + 4)) from e

        # TODO: handle tetrahedra
        lines_tetra = lines[ngrids:]

        return cls(mode, kpts=kpts, weights=weights, comment=comment)


def get_qp_energies_from_outcar(path_outcar, qp_iteration: int = -1, extract_KS: bool = False):
    """Get the quasi-particle energies from the OUTCAR file

    Args:
        path_outcar (str) : path to the OUTCAR file
        qp_iteration (int) : index of iteration to use, starting from 0.
            -1 means last iteration
        extract_KS (bool) : if True, will reture the Kohn-Sham energies instead of QP.
            Particularly, extract_KS True and qp_iteration 0 gives the Kohn-Sham results.

    Returns:
        BandStructure object
    """
    with open_textio(path_outcar, 'r') as h:
        lines = h.readlines()

    nbands_gw = None
    nkpts = None
    nspins = None
    i_first_qp_line = None
    i_col_data = 2
    if extract_KS:
        i_col_data = 1

    # obtain dimension information and starting line of each QP iteration
    for i, line in enumerate(lines):
        if line.startswith("   ISPIN  ="):
            nspins = int(line.split()[2])
        if line.startswith("   k-points           NKPTS ="):
            nkpts = int(line.split()[3])
        if line.startswith(" QP shifts <psi_nk| G(iteration)W_0 |psi_nk>: iteration 1"):
            i_first_qp_line = i

    if nspins > 1:
        raise NotImplementedError("nspins > 1 is not implemented")

    _logger.debug("i_first_qp_line = %d", i_first_qp_line)
    if i_first_qp_line is None:
        raise ValueError("Cannot find qp shifts data from %r" % path_outcar)

    # prune unnecessary lines, get number of GW iterations
    lines = lines[i_first_qp_line:]
    i_kpts = []
    for i, line in enumerate(lines):
        if line.startswith(" k-point "):
            i_kpts.append(i)
    n_ite = len(i_kpts) // nkpts

    # check the first k-point of first iteration to get number of QP states
    i = i_kpts[0] + 3
    l = lines[i]
    while l:
        i += 1
        l = lines[i].strip()
    nbands_gw = i - 3 - i_kpts[0]
    _logger.debug("ispin = %d, nkpts = %d, nbands_gw = %d, n_ite = %d",
                  nspins, nkpts, nbands_gw, n_ite)

    i_ite = qp_iteration
    if i_ite < 0:
        i_ite = n_ite + qp_iteration

    # extract data of the specified iteration and process with numpy
    slist = []
    kpts = []
    for i in i_kpts[i_ite * nkpts: (i_ite + 1) * nkpts]:
        kpts.append([float(x) for x in lines[i].split()[3:]])
        slist.extend(lines[i + 3: i + 3 + nbands_gw])
    ene, occ = np.loadtxt(StringIO("".join(slist)), unpack=True, usecols=[i_col_data, 7])
    ene = np.reshape(ene, (nspins, nkpts, nbands_gw))
    occ = np.reshape(occ, (nspins, nkpts, nbands_gw))
    kpts = np.array(kpts)

    return BandStructure(ene, occ=occ), kpts


def get_bandstructure_outcar_wannier(path_outcar):
    """Get the band structure from the OUTCAR of a Wannier intepolation

    Args:
        path_outcar (str)

    Returns:
        BandStructure objects, ndarray of kpoints
    """
    with open_textio(path_outcar, 'r') as h:
        lines = h.readlines()

    # The eigenvalues are right after the Fermi energy.
    # Get the Fermi energy and prune the unnecessary lines
    i_fermi = None
    efermi = None
    nkpts = None
    nspins = None

    for i, line in enumerate(lines):
        if line.startswith("   ISPIN  ="):
            nspins = int(line.split()[2])
        if line.startswith("   k-points           NKPTS ="):
            nkpts = int(line.split()[3])
        if line.startswith(" E-fermi :"):
            i_fermi = i
            efermi = float(line.split()[2])
            break
    if nspins is None or i_fermi is None or nkpts is None:
        raise ValueError("Fail to find ISPIN, E-fermi or NKPTS")

    lines = lines[i_fermi:]
    i_kpts = []
    for i, line in enumerate(lines):
        if line.startswith(" k-point "):
            i_kpts.append(i)

    # check the first k-point of first iteration to get number of QP states
    i = i_kpts[0] + 2
    l = lines[i]
    while l:
        i += 1
        l = lines[i].strip()
    nbands = i - 2 - i_kpts[0]

    # extract data of the specified iteration and process with numpy
    slist = []
    kpts = []
    for i in i_kpts:
        kpts.append([float(x) for x in lines[i].split()[3:]])
        slist.extend(lines[i + 2: i + 2 + nbands])
    ene, occ = np.loadtxt(StringIO("".join(slist)), unpack=True, usecols=[1, 2])
    ene = np.reshape(ene, (nspins, nkpts, nbands))
    occ = np.reshape(occ, (nspins, nkpts, nbands))
    kpts = np.array(kpts)

    return BandStructure(ene, occ=occ, efermi=efermi), kpts
