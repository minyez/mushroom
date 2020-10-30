# -*- coding: utf-8 -*-
"""classes that manipulate WIEN2k inputs and outputs"""
from copy import deepcopy

import numpy as np

from mushroom.core.cell import Cell
from mushroom.core.ioutils import get_cwd_name
from mushroom.core.crystutils import (get_latt_vecs_from_latt_consts,
                                      get_all_atoms_from_symops)
from mushroom.core.logger import create_logger

__all__ = [
        "Struct",
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
    mult = int(lines[0].split()[1])
    #isplit = int(lines[0].split()[3])

    for i in range(mult):
        l = lines[i + 1]
        p = list(map(float, [l[12:22], l[25:35], l[38:48]]))
        posi.append(p)
    # the line including atomic symbol, NPT, R0, RMT and Z
    l = lines[mult + 1]

    at = l[:2].strip()
    atom = []
    for _ in range(mult):
        atom.append(at)
    npt = int(l[15:20])
    rzero = float(l[25:36])
    rmt = float(l[40:53])
    return atom, posi, npt, rzero, rmt


def _read_symops(lines):
    """Read lines containing symmetry information in struct file

    Args:
        lines (list of str):
    
    Returns:
        dict with two keys, "rotations" and "translations"
    """
    nops = int(lines[0].split()[0])
    symops = {"rotations": np.zeros((nops, 3, 3)), "translations": np.zeros((nops, 3))}
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

class Struct:
    """object for generating struct files"""
    def __init__(self, latt, atms_ineq, posi_ineq, kind="P",
                 npts=None, rzeros=None, rmts=None, symops=None,
                 reference=None, comment=None):
        self.symops = symops
        self.kind = kind
        self.atms_ineq = deepcopy(atms_ineq)
        self.posi_ineq = deepcopy(posi_ineq)
        if symops is None:
            self.symops = {"rotations": [np.diag(3),],
                           "translations": [np.zero(3),]}
        # TODO not very robust way to use lattice kind keyword
        if kind == "F":
            atms_ineq = [*atms_ineq,] * 4
            posi_ineq = np.stack([*posi_ineq,
                                  *np.add(posi_ineq, [0.0, 0.5, 0.5]),
                                  *np.add(posi_ineq, [0.5, 0.0, 0.5]),
                                  *np.add(posi_ineq, [0.5, 0.5, 0.0]),
                                  ])
            posi_ineq = np.mod(posi_ineq, 1.0)
        # get_all_atoms_from_symops will handle the duplicate atoms in
        # above kind detection
        atms, posi = get_all_atoms_from_symops(atms_ineq, posi_ineq, self.symops)
        self.cell = Cell(latt, atms, posi, unit="au", coord_sys="D",
                         reference=reference, comment=comment)
        self.npts = None
        self.rzeros = None
        self.rmts = None
        self.__init_npts(npts)
        self.__init_rzeros(rzeros)
        self.__init_rmts(rmts)
        self.comment = self.cell.comment

    def get_reference(self):
        """get the reference"""
        return self.cell.get_reference()
    
    def __init_npts(self, npts):
        self.npts = []
        if npts is None:
            for _, _ in enumerate(self.atms_ineq):
                self.npts.append(npt_default)
            return
        if isinstance(npts, int):
            for _, _ in enumerate(self.atms_ineq):
                self.npts.append(npts)
            return
        if isinstance(npts, dict):
            for _, atm in enumerate(self.atms_ineq):
                self.npts.append(npts.get(atm))
            return
        self.npts = npts

    def __init_rzeros(self, rzeros):
        self.rzeros = []
        if rzeros is None:
            for _, atm in enumerate(self.atms_ineq):
                self.rzeros.append(_get_default_rzero(atm))
            return
        if isinstance(rzeros, float):
            for _, _ in enumerate(self.atms_ineq):
                self.rzeros.append(rzeros)
            return
        if isinstance(rzeros, dict):
            for _, atm in enumerate(self.atms_ineq):
                self.rzeros.append(rzeros.get(atm))
            return
        self.rzeros = rzeros

    def __init_rmts(self, rmts):
        self.rmts = []
        if rmts is None:
            for _, atm in enumerate(self.atms_ineq):
                self.rmts.append(_get_default_rmt(atm))
            return
        if isinstance(rmts, float):
            for _, _ in enumerate(self.atms_ineq):
                self.rmts.append(rmts)
            return
        if isinstance(rmts, dict):
            for _, atm in enumerate(self.atms_ineq):
                self.rmts.append(rmts.get(atm))
            return
        self.rmts = rmts

    @property
    def natm(self):
        """number of atoms in the cell"""
        return self.cell.natm

    @property
    def latt(self):
        """lattice vector of the cell"""
        return self.cell.latt

    @property
    def natm_ineq(self):
        """number of inequivalent"""
        return len(self.atms_ineq)

    def __str__(self):
        s = ""
        return s

    # pylint: disable=R0914
    @classmethod
    def read(cls, pstruct=None):
        """Read the object from an existing struct file

        Args:
            pstruct (str): path to the file to read as WIEN2k struct
        """
        if pstruct is None:
            pstruct = get_cwd_name() + ".struct"
        with open(pstruct, "r") as h:
            lines = h.readlines()

        natm_ineq = int(lines[1].split()[2])
        kind = lines[1][:4].strip()
        latt_consts = map(lambda i: float(lines[3][10*i:10*i+10]), range(6))
        mode = lines[2][13:].strip()
        latt = get_latt_vecs_from_latt_consts(*latt_consts)

        atm_blocks = []
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
                atm_blocks.append(tuple([s, i + 2]))
                new_atom = True
            if l.endswith("SYMMETRY OPERATIONS"):
                symops_startline = i
                break
        if len(atm_blocks) != natm_ineq:
            raise ValueError("number of atom types read is inconsistent with the file head")

        atms_ineq = []
        posi_ineq = []
        npts = {}
        rzeros = {}
        rmts = {}

        for s, l in atm_blocks:
            atm, p, npt, rzero, rmt = _read_atm_block(lines[s:l+1])
            atms_ineq.extend(atm)
            posi_ineq.extend(p)
            npts[atm[0]] = npt
            rzeros[atm[0]] = rzero
            rmts[atm[0]] = rmt
        symops = _read_symops(lines[symops_startline:])
        return cls(latt, atms_ineq, posi_ineq, npts=npts, symops=symops, rmts=rmts,
                   kind=kind, rzeros=rzeros, comment=lines[0].strip())
    

