# -*- coding: utf-8 -*-
"""classes that manipulate WIEN2k inputs and outputs"""
import pathlib
from os import PathLike
from io import StringIO
from typing import Sequence, Union
import re

import numpy as np

from mushroom.core.cell import Cell
from mushroom.core.elements import NUCLEAR_CHARGE
from mushroom.core.ioutils import grep, print_file_or_iowrapper, get_filename_wo_ext
from mushroom.core.crystutils import (get_latt_vecs_from_latt_consts,
                                      atms_from_sym_nat,
                                      get_latt_consts_from_latt_vecs)
from mushroom.core.logger import create_logger
from mushroom.core.bs import BandStructure

__all__ = [
        "Struct",
        "read_energy",
        ]

_logger = create_logger("wien2k")
del create_logger

npt_default = 781
rzero_default = 0.0001
rzero_default_elements = {}
rmt_default = 1.8
rmt_default_elements = {}

def _get_default_rzero(element):
    """get the default R0 for element ``element``

    Args:
        element (str): element symbol

    Returns:
        float, default R0
    """
    rzero = rzero_default_elements.get(element, None)
    if rzero is None:
        _logger.warning("unknown element for R0, use default %f", rzero_default)
        return rzero_default
    return rzero

def _get_default_rmt(element):
    """get the default RMT for element ``element``

    Args:
        element (str): element symbol

    Returns:
        float, default RMT
    """
    rmt = rmt_default_elements.get(element, None)
    if rmt is None:
        _logger.warning("unknown element for RMT, use default %f", rmt_default)
        return rmt_default
    return rmt

def _read_atm_block(lines):
    """read inequivalent atom block in struct file
    
    Args:
        lines (list of str): the lines of file containing
            information of a particular inequivalent atom

            the first line should start with "ATOM", and
            the local rotation matrix is included
    
    Returns:
        atm, pos, rzero, rmt
    """
    posi = []
    # swicth the first-atom line and mult line for convenience
    lines[0], lines[1] = lines[1], lines[0]
    mult = int(lines[0][15:17])
    isplit = int(lines[0][34:36])

    for i in range(mult):
        l = lines[i + 1]
        p = list(map(float, [l[12:22], l[25:35], l[38:48]]))
        posi.append(p)
    # the line including atomic symbol, NPT, R0, RMT and Z
    l = lines[mult + 1]
    # atom symbol may include an index
    atm = l[:3]
    npt = int(l[15:20])
    rzero = float(l[25:36])
    rmt = float(l[40:53])
    return atm, posi, npt, rzero, rmt, isplit


def _read_symops(lines):
    """Read lines containing symmetry information in struct file

    Args:
        lines (list of str):
    
    Returns:
        dict with two keys, "rotations" and "translations"
    """
    nops = int(lines[0].split()[0])
    symops = {"rotations": np.zeros((nops, 3, 3), dtype='int'),
              "translations": np.zeros((nops, 3))}
    for i in range(nops):
        st = 4 * i + 1
        r = np.array([
            list(map(int, [lines[st + j][0:2], lines[st + j][2:4], lines[st + j][4:6]]))
            for j in range(3)
        ])
        t = np.array(list(map(float, [lines[st + j][7:] for j in range(3)])))
        symops["rotations"][i, :, :] = r
        symops["translations"][i, :] = t
    return symops

def get_casename(dirpath: Union[str, PathLike] = ".", casename: str = None):
    """get the case name of the wien2k calculation under directory `dirpath`
    
    It will first search for .struct file under dirpath and
    return the filename without extension if found.
    Otherwise the name of the directory will be returned

    Args:
        dirpath (str) : the path to the wien2k working directory
        casename (str) : manually specified casename.
            if casename.struct is not found under dirpath,
            FileNotFoundError will be raised
    """
    if isinstance(dirpath, str):
        dirpath = pathlib.Path(dirpath)
    abspath = dirpath.resolve()
    if abspath.is_dir():
        if casename is not None:
            tentative = abspath / "{}.struct".format(casename)
            if tentative.exists():
                return casename
            raise FileNotFoundError("{}.struct is not found under {}".format(casename, abspath))
        for filename in abspath.glob("*.struct"):
            return get_filename_wo_ext(filename)
        return abspath.name
    raise TypeError("{} is not a directory".format(abspath))


def search_cplx_input(path: Union[str, PathLike]) -> str:
    """check if input file for complex calculation is available.

    Args:
        path (PathLike): the path of input file, with extension.
    
    Returns:
        str, the path to the complex input file if found.
             the input path is directed returned, if the path does not have an extension of input
    """
    if isinstance(path, str):
        path = pathlib.Path(path)
    ext = path.suffix
    if ext in [".in1", ".in2"]:
        pathc = pathlib.Path(str(path) + "c")
        if pathc.is_file():
            return str(pathc)
    return str(path)
    

def get_inputs(suffix: str, *suffices, dirpath: Union[str, PathLike] = ".",
               casename: str = None, relative: Union[bool, str, PathLike] = None,
               search_cplx=True):
    """get path of input files given the suffices

    Args:
        suffix and suffices (str): suffices of input files to get
        dirpath (path-like)
        relative (str) : if set to PathLike, the output will be relative file paths to `relative`.
            If set to true, only the filenames will be returned
            If set to CWD, it will return the filenames relative to current directory

    Returns:
        list, the absolute path of input files
    """
    suffices = [suffix,] + list(suffices)
    if isinstance(dirpath, str):
        dirpath = pathlib.Path(dirpath)
    home = dirpath.resolve()
    if relative is not None:
        if relative is True:
            relative = home
        elif relative == "CWD":
            relative = pathlib.Path('.').resolve()
        home = home.relative_to(relative)
    casename = get_casename(dirpath=dirpath, casename=casename)
    inputs = [home / "{}.{}".format(casename, s) for s in suffices]
    if search_cplx:
        return tuple(search_cplx_input(i) for i in inputs)
    return tuple(str(i) for i in inputs)

class Struct:
    """object for generating struct files

    Args:
        atms_types: symbols of each type of nonequivalent atoms
        posi_types: direct positions of atoms of each type in atms_types
            atms_types and posi_types should have the same length
    """
    # pylint: disable=R0912,R0914,R0915
    def __init__(self, latt, atms_types: Sequence[str],
                 posi_types, kind="P", unit="au", coord_sys="D",
                 isplits=None, npts=None, rzeros=None, rmts=None, symops=None,
                 mode: str = "rela",
                 rotmats=None, reference: str = None, comment: str = None):
        if len(atms_types) != len(posi_types):
            raise ValueError("length of atms_types ({}) and posi_types ({}) are different"\
                             .format(len(atms_types), len(posi_types)))
        try:
            assert len(np.shape(posi_types)) == 3
            assert np.shape(posi_types)[2] == 3
        except (AssertionError, ValueError):
            raise ValueError("invalid shape of posi_types")
        self.kind = kind
        self.atms_types = atms_types
        self.isplits = isplits
        if isplits is None:
            self.isplits = [2,] * len(self.atms_types)
        self.rotmats = rotmats
        if rotmats is None:
            self.rotmats = []
            for i, _ in enumerate(atms_types):
                self.rotmats.append(np.diag([1.0, 1.0, 1.0]))
        self.symops = symops
        if symops is None:
            self.symops = {"rotations": [np.diag((1, 1, 1)),],
                           "translations": [np.zeros(3),]}
        posi = []
        natm_types = []
        if kind == "F":
            for p in posi_types:
                posi.extend([*p, *np.add(p, [0.0, 0.5, 0.5]),
                             *np.add(p, [0.5, 0.0, 0.5]), *np.add(p, [0.5, 0.5, 0.0]),
                            ])
                natm_types.append(len(p)*4)
        elif kind == "I":
            for p in posi_types:
                posi.extend([*p, *np.add(p, [0.5, 0.5, 0.5]),
                            ])
                natm_types.append(len(p)*2)
        elif kind in ["P", "H", "R"]:
            for p in posi_types:
                posi.extend(p)
                natm_types.append(len(p))
        else:
            raise ValueError("Unsupported lattice type {}".format(kind))
        posi = np.round(posi, decimals=8)
        atms = atms_from_sym_nat(atms_types, natm_types)
        self._cell = Cell(latt, atms, posi, unit=unit, coord_sys=coord_sys,
                          reference=reference, comment=comment)
        self._cell.move_atoms_to_first_lattice()
        # reset units and coordinate system
        self._cell.unit = "au"
        self._cell.coord_sys = "D"
        self.npts = None
        self.rzeros = None
        self.rmts = None
        self.mode_calc = mode
        self.__init_npts(npts)
        self.__init_rzeros(rzeros)
        self.__init_rmts(rmts)
        self.comment = self._cell.comment
        _logger.debug(">  finish building Struct")
        _logger.debug(">> atms_types: %r", self.atms_types)
        _logger.debug(">>types(cell): %r", self._cell.atom_types)
        _logger.debug(">> isplits: %r", self.isplits)
        _logger.debug(">>    npts: %r", self.npts)
        _logger.debug(">>  rzeros: %r", self.rzeros)
        _logger.debug(">>    rmts: %r", self.rmts)
        _logger.debug(">> rotmats: %r", self.rotmats)

    def get_reference(self):
        """get the reference"""
        return self._cell.get_reference()

    def get_symops(self):
        """get the symmetry operations

        Returns:
            ndarray, ndarry
        """
        rots, trans = map(self.symops.get, ["rotations", "translations"])
        return rots, trans

    def get_cell(self):
        """get the Cell object of Struct"""
        return self._cell


    def __init_npts(self, npts):
        self.npts = []
        if npts is None:
            for _, _ in enumerate(self.atms_types):
                self.npts.append(npt_default)
            return
        if isinstance(npts, int):
            for _, _ in enumerate(self.atms_types):
                self.npts.append(npts)
            return
        if isinstance(npts, dict):
            for _, atm in enumerate(self.atms_types):
                self.npts.append(npts.get(atm))
            return
        self.npts = npts

    def __init_rzeros(self, rzeros):
        self.rzeros = []
        if rzeros is None:
            for _, atm in enumerate(self.atms_types):
                self.rzeros.append(_get_default_rzero(atm))
            return
        if isinstance(rzeros, float):
            for _, _ in enumerate(self.atms_types):
                self.rzeros.append(rzeros)
            return
        if isinstance(rzeros, dict):
            for _, atm in enumerate(self.atms_types):
                self.rzeros.append(rzeros.get(atm))
            return
        self.rzeros = rzeros

    def __init_rmts(self, rmts):
        self.rmts = []
        if rmts is None:
            for _, atm in enumerate(self.atms_types):
                self.rmts.append(_get_default_rmt(atm))
            return
        if isinstance(rmts, float):
            for _, _ in enumerate(self.atms_types):
                self.rmts.append(rmts)
            return
        if isinstance(rmts, dict):
            for _, atm in enumerate(self.atms_types):
                self.rmts.append(rmts.get(atm))
            return
        self.rmts = rmts

    @property
    def natm(self):
        """number of atoms in the cell"""
        return self._cell.natm

    @property
    def atms(self):
        """all atoms in the cell"""
        return self._cell.atms

    @property
    def posi(self):
        """positions of all atoms in direct coordinates"""
        return self._cell.posi

    @property
    def latt(self):
        """lattice vector of the cell"""
        return self._cell.latt

    @property
    def ntypes(self):
        """number of atomic types"""
        return len(self.atms_types)

    def __str__(self):
        return self.export()

    @classmethod
    def from_cell(cls, cell: Cell):
        """build the Struct object from Cell object"""
        atms_types = cell.atom_types
        posi_types = []
        for a in atms_types:
            posi_types.append(cell.get_atm_posi(a))
        return cls(cell.latt, atms_types, posi_types, unit=cell.unit,
                   reference=cell.get_reference(), comment=cell.comment,
                   coord_sys=cell.coord_sys)

    # pylint: disable=R0914
    @classmethod
    def read(cls, pstruct=None):
        """Read the object from an existing struct file

        Args:
            pstruct (str): path to the file to read as WIEN2k struct
        """
        if pstruct is None:
            pstruct = get_casename() + ".struct"
        with open(pstruct, "r") as h:
            lines = h.readlines()

        ntypes = int(lines[1].split()[2])
        kind = lines[1][:4].strip()
        latt_consts = map(lambda i: float(lines[3][10*i:10*i+10]), range(6))
        mode = lines[2][13:].strip()
        latt = get_latt_vecs_from_latt_consts(*latt_consts)

        atm_blocks = []
        rotmats = []
        new_atom = True
        # divide lines into block of atoms and symmetry operations
        for i, line in enumerate(lines):
            if i < 4:
                continue
            l = line.strip()
            if l.startswith("ATOM") and new_atom:
                s = i
                new_atom = False
            if l.startswith("LOCAL ROT MATRIX"):
                rotmats.append(np.loadtxt(StringIO("".join(x[20:] for x in lines[i:i+3]))))
                atm_blocks.append(tuple([s, i + 2]))
                new_atom = True
            if l.endswith("SYMMETRY OPERATIONS"):
                symops_startline = i
                break
        if len(atm_blocks) != ntypes:
            raise ValueError("number of atom types read is inconsistent with the file head")

        atms_types = []
        posi_types = []
        isplits = []
        npts = {}
        rzeros = {}
        rmts = {}

        for s, l in atm_blocks:
            atm, p, npt, rzero, rmt, isplit = _read_atm_block(lines[s:l+1])
            atms_types.append(atm)
            posi_types.append(p)
            isplits.append(isplit)
            npts[atm] = npt
            rzeros[atm] = rzero
            rmts[atm] = rmt
        symops = _read_symops(lines[symops_startline:])
        return cls(latt, atms_types, posi_types, npts=npts, symops=symops, rmts=rmts,
                   isplits=isplits, kind=kind, rzeros=rzeros, rotmats=rotmats, 
                   comment=lines[0].strip())

    def export(self, scale: float = 1.0) -> str:
        """export the cell and atomic setup in the wien2k format"""
        slist = ["{}, {}".format(self.comment, self.get_reference()),
                 "{:<4s}LATTICE,NONEQUIV.ATOMS:{:3d}".format(self.kind, self.ntypes),
                 "MODE OF CALC={}".format(self.mode_calc.upper()),]
        latt_consts_form = "{:10.6f}" * 6
        a1, a2, a3, angle1, angle2, angle3 = get_latt_consts_from_latt_vecs(self.latt)
        slist.append(latt_consts_form.format(a1*scale, a2*scale, a3*scale, angle1, angle2, angle3))
        self._cell.move_atoms_to_first_lattice()
        # write each inequiv atoms
        for iat, (at, rotmat, npt, rzero, rmt, isplit) in enumerate(zip(self.atms_types,
                                                                        self.rotmats,
                                                                        self.npts,
                                                                        self.rzeros,
                                                                        self.rmts,
                                                                        self.isplits)):
            posi = self._cell.get_atm_posi(at)
            mult = len(posi)
            Z = NUCLEAR_CHARGE.get(re.sub(r"[\d ]", "", at))
            slist_atm = ["ATOM{:4d}: X={:10.8f} Y={:10.8f} Z={:10.8f}".format(iat+1,
                                                                              *posi[0, :]),
                         "           MULT={:2d}{:10s}ISPLIT={:2d}".format(mult, "", isplit),]
            for i in range(1, mult):
                slist_atm.append("{:8d}: X={:10.8f} Y={:10.8f} Z={:10.8f}".format(iat+1,
                                                                                  *posi[i, :]))
            slist_atm.append("{:<3s}{:<6s}  NPT={:5d}  R0={:10.8f} RMT={:10.4f}{:>5s}{:5.1f}"\
                             .format(at, "", npt, rzero, rmt, "Z:", Z))
            rotmat_format = "\n".join(["{:<20s}{:10.7f}{:10.7f}{:10.7f}",] * 3)
            slist_atm.append(rotmat_format.format("LOCAL ROT MATRIX", *rotmat[0, :],
                                                  "", *rotmat[1, :],
                                                  "", *rotmat[2, :]))
            slist.extend(slist_atm)
        # write symmetry operations
        rots, trans = self.get_symops()
        slist.append("{:4d}      NUMBER OF SYMMETRY OPERATIONS".format(len(rots)))
        for i, (rot, tran) in enumerate(zip(rots, trans)):
            for j in range(3):
                slist.append("{:2d}{:2d}{:2}{:11.8f}".format(*rot[j, :], tran[j]))
            slist.append("{:8d}".format(i+1))
        return "\n".join(slist)

    def write(self, filename=None, scale: float = 1.0):
        """write the w2k formatted string to filename
        """
        print_file_or_iowrapper(self.export(scale=scale), f=filename)
        

class In1:
    """class for in1 file

    Args:
        casename (str) :
        efermi (float) : fermi energy in Rydberg unit
        lmax (int) 
        lnsmax (int) 
        elparams : linearization energy parameters
    """
    def __init__(self, casename: str, efermi: float, rkmax: float, lmax: int,
                 lnsmax: int, *elparams):
        self.casename = casename
        self.efermi = efermi
        self.rkmax = rkmax
        self.lmax = lmax
        self.lnsmax = lnsmax
        self.elparams = elparams

    @classmethod
    def read(cls, pin1: PathLike = None):
        """Return In1 instance by reading an exisiting file

        Args:
            pin1 (PathLike): the path to the in1 file.
                Left as default to automatic detect under CWD
        """
        if pin1 is None:
            casename = get_casename()
            pin1 = get_inputs("in1", casename=casename, search_cplx=True)
        else:
            casename = get_filename_wo_ext(str(pin1))
        if isinstance(pin1, str):
            pin1 = pathlib.Path(pin1)
        with pin1.open('r') as h:
            w2klines = h.readlines()
        #switch = w2klines[0][:5]
        matched = re.search(r"EF=(-?\d*\.\d+)", w2klines[0])
        if matched is None:
            raise ValueError("Fail to find Fermi energy from in1")
        efermi = float(matched.group(1))
        matched = re.match(r"([-\d\s.]+)", w2klines[1])
        if matched is None:
            raise ValueError("Fail to find RKmax, Lmax and LNSmax from in1")
        rkmax, lmax, lnsmax = map(float, matched.group(1).split())
        lmax = int(lmax)
        lnsmax = int(lnsmax)

        # TODO read linearization energies
        elparams = []
        #i = 2
        #while i < len(w2klines):
        #    line = re.match(r"([-\w\d\s.]+)", w2klines[i]).group()
        #    if line.startswith("K-VECTORS FROM UNIT"):
        #        break
        #    words = line.split()
        #    if len(words) == 3:
        #        ndiff = int(words[1])
        #        atomEl = _read_el_block(w2klines[i : i + ndiff + 1])
        #        elparams.append(atomEl)
        #        i += ndiff
        #    i += 1
        return cls(casename, efermi, rkmax, lmax, lnsmax, *elparams)


# pylint: disable=C0301
# kpoint line format in energy file, wien2k v14.2
_energy_kpt_line = re.compile(r"([ -]\d\.\d{12}E[+-]\d{2})([ -]\d\.\d{12}E[+-]\d{2})([ -]\d\.\d{12}E[+-]\d{2})([\w\s\d]{10})\s*(\d+)\s+(\d+)\s+(\d+\.\d+)")

def _read_efermi_from_second_to_last_el(l):
    """extract the fermi energy from the line containing linearization energy of lapw at large l

    Such energy is usually set to 0.2 Ry below the Fermi level.
    here use the second to the last

    Args:
        l (str): the line containing linearization energy at angular momenta,
            usually the first line of case.energy
    """
    efermi = 0.0
    nel = l.count('.')
    if len(l) % nel != 0:
        raise ValueError("bad-formatted el string")
    width = len(l) // nel
    decimals = width - l.index('.') - 1
    efermi = float(l[-2*width:-width]) + 0.2
    if efermi > 150: # LAPW
        efermi -= 200.0
    return np.around(efermi, decimals=decimals)

def read_energy(penergy: str, penergy_dn: str = None, efermi=None):
    """get a BandStructure instance from the wien2k energy file

    Args:
        penergy (str) : path to the energy file.
            if penergy_dn is also parsed, penergy is treated as the spin-up eigenvalues
        penergy_dn (str) : path to the eneryg file for spin-down channel
        efermi (float): fermi energy. can be extracted from casename.output2 beforehand

    Notes:
        since in occupation numbers are not available in the energy file,
        one need explictly parse the fermi enery

    Returns:
        kpoints, weights, BandStructure
    """
    def _read_one_energy_file(fp, ln_kpts, nb):
        eigen = []
        lines = fp.readlines()
        for ln in ln_kpts:
            _logger.debug("starting k-line %d: %s", ln, lines[ln])
            s = StringIO("".join(lines[ln+1:ln+1+nb]))
            eigen.append(np.loadtxt(s, usecols=[1,]))
        return np.array(eigen)
    if efermi is None:
        try:
            with open(penergy, 'r') as h:
                efermi = _read_efermi_from_second_to_last_el(h.readline().strip('\n'))
        except ValueError:
            pass
    kpt_lines, linenums = grep(_energy_kpt_line, penergy, error_not_found=True,
                               return_linenum=True, return_group=True)
    natm_ineq = linenums[0] // 2
    kpts = []
    nbands = []
    weights = []
    for mg in kpt_lines:
        kpts.append(list(map(float, [mg.group(1), mg.group(2), mg.group(3)])))
        nbands.append(int(mg.group(6)))
        weights.append(float(mg.group(7)))
    weights = np.array(weights) / sum(weights)
    nbands_min = min(nbands)
    _logger.debug("minimal nbands = %d", nbands_min)
    eigen = []
    with open(penergy, 'r') as h:
        eigen.append(_read_one_energy_file(h, linenums, nbands_min))
    if penergy_dn is not None:
        _, linenums = grep(_energy_kpt_line, penergy_dn, error_not_found=True,
                           return_linenum=True)
        eigen.append(_read_one_energy_file(h, linenums, nbands_min))
    # always Rydberg unit
    return BandStructure(eigen, weight=weights, unit='ry', efermi=efermi), natm_ineq, kpts

