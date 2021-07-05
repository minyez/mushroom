# -*- coding: utf-8 -*-
"""classes that manipulate WIEN2k inputs and outputs"""
import pathlib
from io import StringIO
from typing import Sequence, Union, Tuple
import re

import numpy as np

from mushroom.core.cell import Cell
from mushroom.core.constants import SQRT3
from mushroom.core.typehint import Path
from mushroom.core.elements import get_atomic_number
from mushroom.core.ioutils import (grep, print_file_or_iowrapper,
                                   get_filename_wo_ext, get_file_ext)
from mushroom.core.crystutils import (get_latt_vecs_from_latt_consts,
                                      atms_from_sym_nat,
                                      get_latt_consts_from_latt_vecs)
from mushroom.core.logger import create_logger
from mushroom.core.bs import BandStructure
from mushroom.core.dos import DensityOfStates

__all__ = [
        "Struct",
        "read_energy",
        "KList",
        "InTetra",
        "In1",
        ]

_logger = create_logger("w2k")
del create_logger

npt_default = 781
rzero_default_elements = {}
rmt_default = 1.8
rmt_default_elements = {
        "N": 1.4, "B": 1.3
    }

def _get_default_rzero(element):
    """get the default R0 for element ``element``

    Args:
        element (str): element symbol

    Returns:
        float, default R0
    """
    rzero = rzero_default_elements.get(element, None)
    if rzero is None:
        Z = get_atomic_number(element)
        if Z >= 30:
            rzero = 0.00005
        else:
            rzero = 0.0001
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

    l = "".join(lines[mult+2+i][20:].strip('\n') for i in range(3))
    rotmat = np.array([float(l[10*i:10*(i+1)]) for i in range(9)]).reshape((3,3))
    return atm, posi, npt, rzero, rmt, isplit, rotmat


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

def get_casename(dirpath: Path=".", casename: str=None):
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


def search_cplx_input(path: Path) -> str:
    """check if input file for complex calculation is available.

    Args:
        path (Path): the path of input file, with extension.

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


def get_inputs(suffix: str, *suffices, dirpath: Path = ".",
               casename: str = None, relative: Union[bool, Path] = None,
               search_cplx=True) -> Tuple:
    """get path of input files given the suffices

    Args:
        suffix and suffices (str): suffices of input files to get
        dirpath (path-like)
        relative (str) : if set to Path, the output will be relative file paths to `relative`.
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
        latt_consts (6-member tuple): the lattice constants, i.e. a b c alpha beta gamma
        atms_types: symbols of each type of nonequivalent atoms
        posi_types: direct positions of atoms of each type in atms_types
            atms_types and posi_types should have the same length
    """
    # pylint: disable=R0912,R0914,R0915
    def __init__(self, latt_consts, atms_types: Sequence[str],
                 posi_types, kind="P", unit="au", coord_sys="D",
                 isplits=None, npts=None, rzeros=None, rmts=None, symops=None,
                 casename: str=None, mode: str="rela",
                 rotmats=None, reference: str=None, comment: str=None):
        if len(atms_types) != len(posi_types):
            raise ValueError("length of atms_types ({}) and posi_types ({}) are different"\
                             .format(len(atms_types), len(posi_types)))
        #try:
        #    assert len(np.shape(posi_types)) == 3
        #    assert np.shape(posi_types)[2] == 3
        #except (AssertionError, ValueError):
        #    raise ValueError("invalid shape of posi_types")
        self.casename = casename
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
        # the following latt determination are adapted from latgen.f
        # where the reciprocal lattice is calculated first, and then
        # transform to real space with gbass.f
        if kind == "H":
            # recp: [2/SQRT(3), 0, 0], [1/SQRT(3),1,0], [0,0,1]
            latt = [[latt_consts[0], 0, 0],
                    [-latt_consts[0]/2, latt_consts[1]*SQRT3/2, 0],
                    [0, 0, latt_consts[2]]]
        elif kind == "R":
            # recp: [1/SQRT(3), -1, 1], [1/SQRT(3),1,1], [-2/SQRT(3),0,1]
            latt = [[latt_consts[0]/2, latt_consts[1]/2/SQRT3, latt_consts[2]/3],
                    [-latt_consts[0]/2, latt_consts[1]/2/SQRT3, latt_consts[2]/3],
                    [0.0, -latt_consts[1]/SQRT3, latt_consts[2]/3]]
        elif kind == "B":
            # recp:[[0, 1, 1], [1, 0, 1], [1, 1, 0]]
            latt = np.multiply([[-1, 1, 1], [1, -1, 1], [1, 1, -1]], latt_consts[0]/2)
        elif kind in ["CXY", "CYZ", "CXZ"]:
            raise NotImplementedError("C kind of struct is not implemented")
        elif kind == "F":
            # recp:[[-1, 1, 1], [1, -1, 1], [1, 1, -1]]
            latt = np.multiply([[0, 1, 1], [1, 0, 1], [1, 1, 0]], latt_consts[0]/2)
        elif kind in ["P", "S"]:
            # primitive case, generate latt directly
            latt = get_latt_vecs_from_latt_consts(*latt_consts)
        else:
            raise ValueError("Unsupported lattice type {}".format(kind))
        posi = []
        for x in posi_types:
            posi.extend(x)
        posi = np.round(posi, decimals=8)
        self._mults = [len(x) for x in posi_types]
        atms = atms_from_sym_nat(atms_types, self._mults)
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
        self.symops = symops
        if symops is None:
            self.symops = self._cell.get_symops()
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
            # TODO improve default RMT setup by using the nearest-neighbor distance
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
    def mults(self):
        """multipicilty of non-equivalent atoms."""
        return self._mults

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
        return cls(cell.latt_consts, atms_types, posi_types, unit=cell.unit,
                   reference=cell.get_reference(), comment=cell.comment,
                   coord_sys=cell.coord_sys, symops=cell.get_symops())

    # pylint: disable=R0914
    @classmethod
    def read(cls, pstruct: Path = None):
        """Read the object from an existing struct file

        Args:
            pstruct (str): path to the file to read as WIEN2k struct
        """
        if pstruct is None:
            casename = get_casename()
            pstruct = casename + ".struct"
        else:
            casename = get_filename_wo_ext(str(pstruct))

        pstruct = pathlib.Path(pstruct)
        with pstruct.open("r") as h:
            lines = h.readlines()
        # the second: (A4,23X,I3), containing spacegroup information
        ntypes = int(lines[1][27:30])
        kind = lines[1][:4].strip()
        # lattice constants, 6F10.6
        latt_consts = tuple(map(lambda i: float(lines[3][10*i:10*i+10]), range(6)))
        # relativity mode: RELA or something else
        mode = lines[2][13:].strip()

        atm_blocks = []
        rotmats = []
        new_atom = True
        # divide lines into block of atoms and symmetry operations
        # each atom block: n (mult) + 2 (mult&isplit, npt&r0&RMT&Z0) + 3 (rotmat)

        atomline_index = 4

        atms_types = []
        posi_types = []
        isplits = []
        npts = {}
        rzeros = {}
        rmts = {}
        for _ in range(ntypes):
            mult = int(lines[atomline_index+1][15:17])
            atm, p, npt, rzero, rmt, isplit, rotmat = \
                    _read_atm_block(lines[atomline_index:atomline_index+mult+6])
            atms_types.append(atm)
            posi_types.append(p)
            rotmats.append(rotmat)
            isplits.append(isplit)
            npts[atm] = npt
            rzeros[atm] = rzero
            rmts[atm] = rmt
            atomline_index += mult + 5

        symops = _read_symops(lines[atomline_index:])
        return cls(latt_consts, atms_types, posi_types, npts=npts, symops=symops, rmts=rmts,
                   isplits=isplits, kind=kind, rzeros=rzeros, rotmats=rotmats,
                   comment=lines[0].strip(), casename=casename)

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
            Z = get_atomic_number(at)
            slist_atm = ["ATOM{:4d}: X={:10.8f} Y={:10.8f} Z={:10.8f}".format(iat+1,
                                                                              *posi[0, :]),
                         "{:10s}MULT={:2d}{:10s}ISPLIT={:2d}".format("", mult, "", isplit),]
            for i in range(1, mult):
                slist_atm.append("{:8d}: X={:10.8f} Y={:10.8f} Z={:10.8f}".format(iat+1,
                                                                                  *posi[i, :]))
            slist_atm.append("{:<3s}{:<8s}NPT={:5d}  R0={:10.8f} RMT={:10.4f}{:>5s}{:5.1f}"\
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
    def read(cls, pin1: Path=None):
        """Return In1 instance by reading an exisiting file

        Args:
            pin1 (Path): the path to the in1 file.
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
_energy_kpt_line = re.compile(r"([ -]\d\.\d{12}E[+-]\d{2})"*3+r"([\w\s\d]{10})\s*(\d+)\s+(\d+)\s+(\d+\.\d+)")

def _read_efermi_from_second_to_last_el(l, shift_to_last_digit: int=1):
    """extract the fermi energy from the line containing linearization energy of lapw at large l

    Such energy is usually set to 0.2 Ry below the Fermi level.
    here use the second to the last.

    Args:
        l (str): the line containing linearization energy at angular momenta,
            usually the first lines of case.energy
        shift_to_last_digit (int): float added to the detected EF,
            a work around to avoid gap detection in the same band
    """
    _logger.debug("Reading fermi energy from text: %s", l)
    efermi = 0.0
    nel = l.count('.')
    if len(l) % nel != 0:
        raise ValueError("bad-formatted el string")
    width = len(l) // nel
    decimals = width - l.index('.') - 1
    efermi = float(l[-2*width:-width]) + 0.2
    if efermi > 150: # LAPW
        efermi -= 200.0
    _logger.info("> nr. excpetions = %d", nel)
    _logger.info("> read E_F = %f", efermi)
    efermi += shift_to_last_digit * (10 ** (-decimals))
    _logger.info(">  set E_F = %f", efermi)
    return efermi

# pylint: disable=R0914
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
            _logger.debug("starting k-line %d: %s", ln, lines[ln].strip('\n'))
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
    symbols = []
    for ik, mg in enumerate(kpt_lines):
        kpts.append(list(map(float, [mg.group(1), mg.group(2), mg.group(3)])))
        nbands.append(int(mg.group(6)))
        weights.append(float(mg.group(7)))
        try:
            int(mg.group(4))
        except ValueError:
            if mg.group(4).strip():
                symbols.append((ik, mg.group(4).strip()))
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
    return BandStructure(eigen, weight=weights, unit='ry', efermi=efermi), \
           natm_ineq, np.array(kpts), symbols

class KList:
    """the object to manipulate klist file, including

    Args:
        xyzd (int arraylike, (n,4))
        weight (float arraylike, (n))
        e1,e2
        ksym (list of tuple)
        comment (str)
    """
    def __init__(self, xyzd: Sequence[Tuple[int,int,int,int]],
                 weight: Sequence[float], e1: float, e2: float,
                 ksym: Sequence[Tuple[int,str]]=None, comment: str=None):
        self.xyzd = np.array(xyzd)
        self.weight = np.array(weight)
        self.e1 = e1
        self.e2 = e2
        self.ksym = {}
        if ksym is not None:
            for ik, sym in ksym:
                self.ksym[ik] = sym
        self.comment = comment
        self._kpts = None
        self._nkpt = len(self.xyzd)

    def get_kpts(self):
        """get the fractional kpoint vectors"""
        if self._kpts is None:
            self._kpts = self.xyzd[:,:3] / self.xyzd[:,3]
        return self._kpts

    def export(self):
        """export klist as string in the new format"""
        slist = []
        # a band-like klist if symbol is not empty
        bandlike = False
        if self.ksym:
            bandlike = True
        for ik, (x, y, z, d), w in enumerate(zip(self.xyzd, self.weight)):
            if bandlike:
                sym = self.ksym.get(ik, "")
            else:
                sym = str(ik+1)
            s = "{:10s}{:10d}{:10d}{:10d}{:10d}{:5.2f}".format(sym, x, y, z, d, w)
            if ik == 0:
                s = s + "{:5.2f}{:5.2f}{:s}".format(self.e1, self.e2, self.comment)
            slist.append(s)
        return "\n".join(slist)

    @classmethod
    def read(cls, pklist: Path):
        """read a klist file and return a KList object"""
        raise NotImplementedError

class InTetra:
    """int file for qtl/tetra"""
    def __init__(self):
        pass

# pylint: disable=R0912,R0915
def read_qtl(pqtl: Path, data_only: bool=False):
    """read qtl file and return a BandStructure object

    Args:
        pqtl (Paht): path to the qtl file
        data_only (bool): when set True, only the pwav data and prjs will be returned
            instead of the BandStructure object
    Note:
        only SPIN=1 is supported now, i.e. you can only parse on qtl file

    """
    def _read_one_band_block_between_iline(lines, natm):
        nkpt = len(lines)//(natm+1)
        nprj = len(lines[0].split()) - 3
        eig = np.zeros((nkpt,))
        pwav = np.zeros((nkpt, natm, nprj))
        for ik in range(nkpt):
            eig[ik] = float(lines[ik*(natm+1)+natm].split()[0])
            for ia in range(natm):
                l = lines[ik*(natm+1)+ia]
                pwav[ik, ia, :] = list(map(float, l.split()[3:]))
        return nkpt, eig, pwav
    if pqtl is None:
        casename = get_casename()
        pqtl = casename + ".qtl"
    else:
        casename = get_filename_wo_ext(str(pqtl))
    _logger.info("Reading qtl: %s", pqtl)
    with open(pqtl, 'r') as h:
        h.readline()
        h.readline()
        # read fermi energy and natom and multiplicity
        efermi = float(h.readline().split()[-1])
        matched = re.search(r"SPIN=(\d)   NAT=(\s+\d+)", h.readline())
        if matched is None:
            raise ValueError("fail to get spin and atoms from qtl {}".format(pqtl))
        nspin = int(matched.group(1))
        if nspin > 1:
            raise NotImplementedError("ispin>1 is not supported!")
        natm = int(matched.group(2))
        # read projectors and multipilicty
        atlines = []
        for _ in range(natm):
            atlines.append(h.readline())
        mults = [int(re.search(r"MULT=(\s+\d+)", x).group(1)) for x in atlines]
        # remove the first which is total
        prjs = atlines[0].split()[-1].split(',')[1:]
        nprj = len(prjs)
        enes = h.readlines()
    _logger.info("> mults: %r", mults)
    _logger.info(">  prjs: %r", prjs)
    # starting index of BAND block (excluding BAND)
    ibls = []
    for i, s in enumerate(enes):
        if s.startswith(" BAND"):
            ibls.append(i+1)
    nbands = len(ibls)
    list_eigen = []
    list_pwav = []
    for i, ibst in enumerate(ibls):
        if i < nbands - 1:
            nkpt, e, p = _read_one_band_block_between_iline(enes[ibst:ibls[i+1]], natm)
        else:
            nkpt, e, p = _read_one_band_block_between_iline(enes[ibst:], natm)
        list_eigen.append(e)
        list_pwav.append(p)
    eigen = np.zeros((1, nkpt, nbands))
    pwav = np.zeros((1, nkpt, nbands, natm, nprj))
    for ib, (e, p) in enumerate(zip(list_eigen, list_pwav)):
        eigen[0, :, ib] = e
        pwav[0, :, ib, :, :] = p
    # consider multiplicity
    for iat, mult in enumerate(mults):
        pwav[:, :, :, iat, :] = pwav[:, :, :, iat, :]*mult
    # process projectors:
    # angular number to its corresponding name
    # lower letter
    prjs_new = []
    for p in prjs:
        prjs_new.append({"0": "s", "1": "p", "2": "d", "3": "f"}.get(p, p.lower()))
    if data_only:
        return pwav, prjs_new
    return BandStructure(eigen, unit="ry", pwav=pwav, prjs=prjs_new)

def read_dos(pdos1: Path, *pdos: Path, unit: str=None,
             mults: Sequence[int]=None) -> DensityOfStates:
    """read one or more dos(ev) files and return a DensityOfStates object

    Args:
        pdos1 (Path): path to dos1(ev) file
        pdos (Path): path to extra dos(ev) files when many projection were requested
        unit (str): if not set, the unit will be detected by getting the extension of
            pdos1
        mults (tuple of int): multiplicity of atoms

    TODO:
        read Fermi level from the first dos file
    """
    def _load_dos_atms_prjs(fn, n):
        # n is the columns to exclude for projectors
        data = np.loadtxt(fn, unpack=True)
        with open(fn, 'r') as h:
            h.readline()
            h.readline()
            # atom:projector in dos. 1 for the comment symbol
            atms_prjs = h.readline().split()[n+1:]
        return data, atms_prjs
    if unit is None:
        ext = get_file_ext(pdos1)
        if ext.startswith("dos1ev"):
            unit = "ev"
        else:
            unit = "ry"
    data, atms_prjs = _load_dos_atms_prjs(pdos1, 2)
    # extra dos files
    if pdos:
        for p in pdos:
            dp, app = _load_dos_atms_prjs(p, 1)
            # remove the energy column
            data = np.stack([data, dp[1:,:]])
            atms_prjs.extend(app)
    # in dos(ev), efermi is fixed to 0.0
    egrid = data[0,:]
    tdos = data[1,:].reshape((1, len(egrid)))
    # return if no projected dos are found
    if len(atms_prjs) == 0:
        return DensityOfStates(egrid, tdos, efermi=0.0)
    # reshape the projected DOS by atoms and projectors
    atms = []
    prjs = []
    for ap in atms_prjs:
        a, p = ap.split(":")
        if a not in atms:
            atms.append(a)
        if p not in prjs:
            prjs.append(p)
    if mults is None:
        mults = np.ones(len(atms))
    pdos = np.zeros((1, len(egrid), len(atms), len(prjs)))
    for iap, ap in enumerate(atms_prjs):
        a, p = ap.split(":")
        ia = atms.index(a)
        pdos[0, :, ia, prjs.index(p)] = data[2+iap] * mults[ia]
    return DensityOfStates(egrid, tdos, efermi=0.0, unit=unit,
                           pdos=pdos, atms=atms, prjs=prjs)

