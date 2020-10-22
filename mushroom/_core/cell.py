# -*- coding: utf-8 -*-
# pylint: disable=bad-whitespace,too-many-lines
"""Module that defines classes for crystal cell manipulation

The ``cell`` class and its subclasses accept the following kwargs when being instantialized:

    - coord_sys (str): Coordinate system for the internal positions,
      either "D" (Direct, default) or "C" (Cartesian)
    - all_relax (bool) : default selective dynamics option for atoms.
      Set True (default) to allow all DOFs to relax
    - select_dyn (dict) : a dictionary with key-value pair as ``int: [bool, bool, bool]``, 
      which controls the selective dynamic option for atom with the particular index 
      (starting from 0). Default is an empty ``dict``
    - comment (str): message about the cell, e.g. theory level, experimental conditions
    - reference (str): the reference where the lattice structure is derived.

When other keyword are parsed, they will be filtered out and no exception will be raised
"""
import json
import string
import os
from collections import OrderedDict
from numbers import Real
from typing import List
from itertools import product

import numpy as np
try:
    import spglib
except ImportError:
    spglib = None

from mushroom._core.constants import PI
from mushroom._core.cif import Cif
from mushroom._core.elements import NUCLEAR_CHARGE
from mushroom._core.unit import LengthUnit
from mushroom._core.crystutils import (get_latt_consts_from_latt_vecs,
                                       periodic_duplicates_in_cell,
                                       select_dyn_flag_from_axis,
                                       atms_from_sym_nat,
                                       sym_nat_from_atms,
                                       axis_list)
from mushroom._core.ioutils import (grep, get_str_indices,
                                    trim_comment,
                                    get_file_ext,
                                    print_file_or_iowrapper)
from mushroom._core.logger import create_logger


class CellError(Exception):
    """Exception in cell module
    """

_logger = create_logger("cell")
del create_logger


class Cell(LengthUnit):
    """Cell structure class

    Args:
        latt (array-like) : The lattice vectors
        atoms (list of str) : The list of strings of type for each atom 
        corresponding to the member in pos
        pos (array-like) : The internal coordinates of atoms
        unit (str): the unit, in lower case, either "ang" (default) or "au".

    Note:
        see ``cell`` module docstring for acceptable kwargs for ``Cell`` and its subclasses

    Examples:
    >>> Cell([[5.0, 0.0, 0.0], [0.0, 5.0, 0.0], [0.0, 0.0, 5.0]], ["C"], [[0.0, 0.0, 0.0]])
    <mushroom._core.cell.Cell>
    """

    _err = CellError
    _dtype = 'float64'
    avail_exporters = ['vasp', 'abi']

    def __init__(self, latt, atms, posi, unit='ang', sanitize=True, **kwargs):

        self.comment = "Default Cell class"
        self._reference = ''
        self._all_relax = True
        self._select_dyn = {}
        self._coord_sys = 'D'

        try:
            self._latt = np.array(latt, dtype=self._dtype)
            self._posi = np.array(posi, dtype=self._dtype)
        except ValueError:
            raise self._err(
                "Fail to create latt and posi array. Please check.")
        LengthUnit.__init__(self, lunit=unit)
        self._atms = [a.capitalize() for a in atms]
        self._parse_cellkw(**kwargs)
        self._check_input_consistency()
        if sanitize:
            self._sanitize_atoms()
        self.exporters = {
            'vasp': self.export_vasp,
            'abi': self.export_abi,
            }

    def __len__(self):
        return len(self._atms)

    def __getitem__(self, index):
        if isinstance(index, int):
            return self._posi[index, :]
        if isinstance(index, str):
            return self.get_sym_index(index)
        raise self._err("atom index or symbol {} not found".format(index))

    def __str__(self):
        return "{}\nLattice:\n{}\nAtoms: {}\nPositions:\n{}\nUnit: {}\nCoordinates in {}".format(
            self.comment, self.latt, self.atms, self.posi, self.unit, self.coord_sys)

    def __repr__(self):
        return self.__str__()

    def _parse_cellkw(self, **kwargs):
        if 'coord_sys' in kwargs:
            self._coord_sys = kwargs['coord_sys'].upper()
        if "all_relax" in kwargs:
            self._all_relax = kwargs["all_relax"]
        if "select_dyn" in kwargs:
            self._select_dyn = kwargs["select_dyn"]
        if "reference" in kwargs:
            self._reference = "{}".format(kwargs["reference"])
        if "comment" in kwargs:
            self.comment = "{}".format(kwargs["comment"])

    def get_cell(self):
        '''Purge out the cell, atoms and pos.

        ``cell``, ``atoms`` and ``pos`` are the minimal for constructing ``Cell``
        and its subclasses.
        They can also be used to build sysmetry operations with spglib utilities.
        '''
        return self._latt, self._atms, self._posi

    def get_kwargs(self) -> dict:
        '''return all kwargs useful to constract program-dependent cell input from ``Cell`` instance

        Returns :
            dictionary that can be parsed to ``create_from_cell`` class method.
        '''
        _d = {
            "unit": self._lunit,
            "coord_sys": self._coord_sys,
            "comment": self.comment,
            "reference": self._reference,
            "all_relax": self._all_relax,
            "select_dyn": self._select_dyn
        }
        return _d

    def get_reference(self) -> str:
        '''Return the reference of the structure
        '''
        return self._reference

    def _check_input_consistency(self):
        try:
            assert self._coord_sys in ["C", "D"]
            assert np.shape(self._latt) == (3, 3)
            assert self.natm > 0
            assert np.shape(self._posi) == (self.natm, 3)
        except AssertionError:
            raise self._err("Invalid cell setup")
        # ? switch automatically, or let the user deal with it
        try:
            assert self.vol > 0
        except AssertionError:
            raise self._err(
                "Left-handed system found (vol<0). Switch two vector.")

    def _switch_two_atom_index(self, iat1, iat2):
        """switch the index of atoms with index iat1 and iat2

        Except ``_posi`` and ``_atms``,
        this method should also deals possible switch in other positional
        attributes, e.g.

        - ``select_dyn`` (DONE)

        Note that this method is mainly for sorting use, and does NOT change
        the geometry of the cell at all.
        """
        try:
            assert iat1 in range(self.natm)
            assert iat2 in range(self.natm)
            assert iat1 != iat2
        except AssertionError:
            raise self._err(
                "Fail to switch two atoms with indices {} and {}".format(iat1, iat2))

        self._posi[[iat1, iat2]] = self._posi[[iat2, iat1]]
        self._atms[iat1], self._atms[iat2] = self._atms[iat2], self._atms[iat1]

        sfd1 = self._select_dyn.pop(iat1, [])
        sfd2 = self._select_dyn.pop(iat2, [])
        if sfd1 != []:
            self._select_dyn.update({iat2: sfd1})
        if sfd2 != []:
            self._select_dyn.update({iat1: sfd2})

    def move_atoms_to_first_lattice(self):
        '''Move all atoms into the lattice (0,0,0).

        For Cartisian system, the move is achieved by first
        converting to and then back from direct system.
        By this process, each component of the coordinate (in direct system)
        belongs to [0,1)
        '''
        if self.coord_sys == "D":
            self._posi = self._posi - np.floor(self._posi)
        elif self.coord_sys == "C":
            self.coord_sys = "D"
            self._posi = self._posi - np.floor(self._posi)
            self.coord_sys = "C"

    def get_sym_index(self, csymbol):
        '''Get the indices of atoms with element symbol ``csymbol``

        Note that this is equivalent to ``cell[csymbol]``, given cell an instance of ``Cell``.

        Args:
            csymbol (str) : chemical-symbol-like identifier
        '''
        assert isinstance(csymbol, str)
        return get_str_indices(self.atms, csymbol.capitalize())

    # * Sorting method
    def _bubble_sort_atoms(self, key, indices, reverse=False):
        """sort atoms with bubble sort under various scenarios

        The smaller value will appear earlier, if ``reverse`` is left
        as False.
        In both cases, when two same values are compared,
        current bubble will just break.

        Args:
            key (natom-member list): the key value to be sorted
            indices (iterable): the indices of the atoms to be sorted
            reverse (bool): if set True, larger value appears earlier
        """
        _depth = 1
        _logger.debug("Bubble sort with key: %s, indices %r", key, indices)
        ind = list(indices)
        k = [key[i] for i in ind]
        n = len(ind)
        _sorted = True
        for i in range(n - 1):
            li = i
            ri = i+1
            _logger.debug("Check sort index: %d", i)
            __dict = {True: k[li] > k[ri],
                      False: k[li] < k[ri]}
            if not __dict[reverse]:
                _sorted = False
                break
        if not _sorted:
            for i in range(1, n):
                j = i
                while j > 0:
                    li = j-1
                    ri = j
                    __dict = {True: k[ri] > k[li],
                              False: k[ri] < k[li]}
                    if __dict[reverse]:
                        self._switch_two_atom_index(ind[li], ind[ri])
                        k[li], k[ri] = k[ri], k[li]
                        j -= 1
                    else:
                        break

    def _sanitize_atoms(self):
        """Sanitize the atoms arrangement after initialization.

        It mainly deals with arbitrary input of ``atoms`` when initialized.
        """
        self._bubble_sort_atoms(self.type_index(), range(self.natm))

    def sort_posi(self, axis=3, reverse=False):
        '''Sort the atoms by its coordinate along axis.

        The ``atoms`` list will not change by sorting, i.e. the sorting is performed
        within each atomic group.
        If ``reverse`` is False, atom with higher coordinate in lattice (0,0,0)
        will appear earlier, otherwise later.

        This behavior is opposite to ``sort`` functions, in spirit of that surfaces are often
        placed at high along one axis, and sorting in descending order makes the surface
        appear first and easy to modify.

        Args :
            axis (1,2,3)
            reverse (bool)
        '''
        try:
            assert axis in range(1, 4)
            assert isinstance(reverse, bool)
        except AssertionError:
            raise self._err()
        keys = self.posi[:, axis-1]
        for at in self.atom_types:
            ind = self.get_sym_index(at)
            self._bubble_sort_atoms(keys, ind, reverse=not reverse)

    # * Cell manipulation
    def scale(self, scale: float):
        '''Scale the lattice, i.e. increase the lattice by ``scale`` time
        '''
        try:
            assert isinstance(scale, Real)
            assert scale > 0.0
        except AssertionError:
            raise self._err("scale must be positive real")
        self._latt = self._latt * scale
        if self._coord_sys == "C":
            self._posi = self._posi * scale

    def add_atom(self, atom, coord, select_dyn=None, sanitize=True):
        """Add an atom with coordinate and selective dynamic flags

        Args:
            atom (str): the chemical symbol of the atom to add
            coord (array-like): the coordinate of atom in ``Cell`` coordinate system
            select_dyn (list of 3 bools): 
        """
        if not isinstance(atom, str):
            raise CellError("atom should be string, received {}".format(type(atom)))
        try:
            newpos = np.vstack([self._posi, coord])
        except ValueError:
            raise self._err("Invalid coordinate: {}".format(coord))
        if select_dyn is not None:
            self._set_select_dyn({self.natm: select_dyn})
        self._posi = newpos
        self._atms.append(atom)
        self.move_atoms_to_first_lattice()
        if sanitize:
            self._sanitize_atoms()

# pylint: disable=R0914
    def get_supercell(self, n1: int = 1, n2: int = 1, n3: int = 1):
        """create supercell from current

        Note that selective dynamic flags will be lost in the new object.

        Args:
            n1, n2, n3 (int)

        Returns:
            Cell
        """
        was_c = self.coord_sys == "C"
        multi = np.array([n1, n2, n3])
        if np.prod(multi) == 0:
            raise ValueError("encounter zero expansion")

        self.coord_sys = "D"
        latt, atms, posi = self.get_cell()
        scatms = []
        for _ in range(n1*n2*n3):
            scatms.extend(atms)
        sclatt = latt.transpose() * multi
        sclatt = sclatt.transpose()
        posi = posi / multi
        scposi = []
        # n3, n2, n1 to make the first coordinate goes fastest
        for i3, i2, i1 in product(range(n3), range(n2), range(n1)):
            shift = np.ones((self.natm, 3)) * np.divide([i1, i2, i3], multi)
            scposi.extend(posi + shift)
        sc = type(self)(sclatt, scatms, scposi, unit=self.unit, coord_sys="D",
                        comment="{}x{}x{} S.C. of {}".format(n1, n2, n3, self.comment),
                        reference=self.get_reference())
        # convert back to Cartisian
        if was_c:
            self.coord_sys = "C"
            sc.coord_sys = "C"
        return sc

    def primitize(self, standardized: bool = False):
        """get the primitized cell
        
        Args:
            standardized (bool)
        """
        if spglib is None:
            raise ImportError("need spglib to primitize cell")
        print(standardized)
        raise NotImplementedError

    # TODO move atom
    def __move(self, ia):
        raise NotImplementedError

    def __move_all(self, shift):
        '''Move all atoms by a shift
        '''
        assert np.shape(shift) == (3,)
        np.add(self._posi, shift, out=self._posi)

    @property
    def center(self):
        """Calculate the center of all atoms in the cell
        """
        assert self.coord_sys == "D"
        _posSum = np.zeros(3, dtype=self._dtype)
        _n = 0
        for i in range(self.natm):
            _dupcs, _dn = periodic_duplicates_in_cell(self._posi[i, :])
            for _dupc in _dupcs:
                np.add(_posSum, _dupc/float(_dn), _posSum)
        # _posSum = np.sum(self._posi, axis=0)
        # check periodic duplicate, by recognizing number of zeros in pos.
        # _dup = 3 - np.count_nonzero(self._posi, axis=1)
        # _dup = np.power(2, _dup)
        # _n = np.sum(_dup)
        # _posSum = np.sum(self._posi * _dup[:, None], axis=0)
        return _posSum / self.natm

    def centering(self, axis: int = 0):
        '''Centering the atoms along axes. Mainly use for slab model.

        TODO:
            For now not work when there is atom at origin along the axis

        Args:
            axis (int or iterable of int) : the axes along which the atoms will be centered.
        '''
        _alist = axis_list(axis)
        _was_cart = self.coord_sys == "C"
        if _was_cart:
            self.coord_sys = "D"
        # get the geometric center of all atoms
        _center = self.center
        _shift = np.array([0.5, 0.5, 0.5], dtype=self._dtype) - _center

        for i in range(3):
            ia = i + 1
            if ia not in _alist:
                _shift[i] = 0.0
        self.__move_all(_shift)
        #     if self.check_vacuum_pos(zdirt):
        #         self.__print("  - Vacuum in the middle detected. Not supported currently. Pass.")
        #         continue
        #     else:
        #         surf_atom = [self.check_extreme_atom(0.0,zdirt,False,1.0), 
        #                      self.check_extreme_atom(0.0,zdirt,True,1.0)]
        #         # debug
        #         # print surf_atom
        #         shift = 0.5 - sum([self.innerpos[i-1][iz] for i in surf_atom])/2.0
        #         self.action_shift(shift,zdirt)
        # self.__print(" Complete centering.")
        if _was_cart:
            self.coord_sys = "C"

    @property
    def a(self):
        '''Lattice vectors
        '''
        return self._latt

    @property
    def alen(self):
        '''Length of lattice vectors
        '''
        return np.array([np.linalg.norm(x) for x in self._latt], dtype=self._dtype)

    @property
    def latt_consts(self):
        '''Lattice constant of the cell, i.e., a, b, c, alpha, beta, gamma (in degree)
        '''
        return get_latt_consts_from_latt_vecs(self._latt)

    @property
    def latt(self):
        '''Lattice vectors
        '''
        return self._latt

    @property
    def atms(self):
        '''list.'''
        return self._atms

    @property
    def posi(self):
        '''array.'''
        return self._posi

    @property
    def unit(self):
        '''str.'''
        return self._lunit

    @unit.setter
    def unit(self, u):
        coef = self._get_lunit_conversion(u)
        if coef != 1:
            if self._coord_sys == "C":
                self._posi = self._posi * coef
            self._latt = self._latt * coef
            self._lunit = u.lower()

    @property
    def coord_sys(self):
        '''coordinate system
        '''
        return self._coord_sys

    @coord_sys.setter
    def coord_sys(self, sys):
        sys = sys.upper()
        if sys != self._coord_sys:
            _convDict = {"C": self._latt, "D": np.linalg.inv(self._latt)}
            _conv = _convDict.get(sys)
            if _conv is not None:
                self._posi = np.matmul(self._posi, _conv)
                self._coord_sys = sys
            else:
                info = "Only support \"D\" direct or fractional and \"C\" Cartisian coordinate."
                raise CellError(info)

    @property
    def atom_types(self):
        """All atom types in the cell
        """
        _d = OrderedDict.fromkeys(self._atms)
        return list(_d.keys())

    @property
    def type_mapping(self):
        '''Map index (int) to atom type (str)
        '''
        _ats = self.atom_types
        _dict = {}
        for i, _at in enumerate(_ats):
            _dict.update({i: _at})
        return _dict

    def type_index(self, start: int = 0) -> List[str]:
        """Indices of atomic type of all atoms

        Args:
            start (int) : index of the first atomic type
        """
        _ats = self.atom_types
        _dict = {}
        for i, _at in enumerate(_ats):
            _dict.update({_at: i + start})
        return [_dict[_a] for _a in self._atms]

    @property
    def vol(self) -> float:
        """Volume of the cell
        """
        return np.linalg.det(self._latt)

    @property
    def natm(self) -> int:
        """Int. Total number of atoms
        """
        return len(self._atms)

    @property
    def use_select_dyn(self):
        """Bool. If use selective dynamics
        """
        if self._all_relax and not bool(self._select_dyn):
            return False
        return True

    @property
    def recp_latt_2pi(self):
        '''Reciprocal lattice vectors in 2Pi unit^-1
        '''
        b = []
        for i in range(3):
            j = (i + 1) % 3
            k = (i + 2) % 3
            b.append(np.cross(self.latt[j, :], self.latt[k, :]))
        return np.array(b, dtype=self._dtype) / self.vol

    @property
    def b_2pi(self):
        """Alias to ``recp_latt_2pi``
        """
        return self.recp_latt_2pi

    @property
    def recp_latt(self):
        """Reciprocal lattice vectors in unit^-1
        """
        return self.b_2pi * 2.0E0 * PI

    @property
    def b(self):
        """Alias of ``recp_latt``
        """
        return self.recp_latt

    @property
    def blen(self):
        """Length of reciprocal lattice vector in unit^-1
        """
        return np.array([np.linalg.norm(x) for x in self.b], dtype=self._dtype)

    # * selective dynamics related
    def fix_all(self):
        """Fix all atoms.
        """
        self._select_dyn = {}
        self._all_relax = False

    def relax_all(self):
        """Relax all atoms.
        """
        self._select_dyn = {}
        self._all_relax = True

    def set_fix(self, *iats, axis=0):
        """Fix the atoms with index in iats

        Args:
            iats (list of int): the indices of atoms to fix
            axis (int or list): the axes along which the position of atom is fixed
                It can be 0|1|2|3, or a list with all its members 1|2|3
        """
        if len(iats) != 0:
            new = {}
            for i in iats:
                if i in range(self.natm):
                    new.update(
                        {i: select_dyn_flag_from_axis(axis, relax=False)})
            self._set_select_dyn(new)

    def set_relax(self, *iats, axis=0):
        '''Relax the atoms with index in iats

        Args:
            iats (list of int): the indices of atoms to relax
            axis (int or list): the axes along which the position of atom is relaxed
                It can be 0|1|2|3, or a list with all its members 1|2|3
        '''
        if len(iats) != 0:
            _new = {}
            for _ia in iats:
                if _ia in range(self.natm):
                    _new.update(
                        {_ia: select_dyn_flag_from_axis(axis, relax=True)})
            self._set_select_dyn(_new)

    def relax_from_top(self, n, axis=3):
        """Set all atoms fixed, and relax the n atoms from top along axis
        """
        raise NotImplementedError

    def fix_from_center(self, n, axis=3):
        """Set all atoms relaxed, and fix the n atoms from the middle along axis
        """
        raise NotImplementedError

    def _set_select_dyn(self, flags):
        """Set the flags for selective dynamics"""
        try:
            assert isinstance(flags, dict)
        except AssertionError:
            raise self._err("need dictionary to set selective dynamics")
        for flag in flags.values():
            try:
                assert isinstance(flag, list)
                assert len(flag) == 3
                assert all([isinstance(_x, bool) for _x in flag])
            except AssertionError:
                raise self._err("Bad flag for selective dynamics")
        self._select_dyn.update(flags)

    def sd_flag(self, ia=-1):
        '''Return the selective dynamic flag (bool) of an atom

        Args:
            ia (int) : index of atom

        Returns:
            3-member list, if ia is in range(natm),
            otherwise natm-member list, each member a 3-member list
            as the flag for that atom
        '''
        if ia in self._select_dyn:
            flag = self._select_dyn[ia]
        elif ia in range(self.natm):
            # self.print_log("Use global flag for atom {}".format(ia), level=3, depth=1)
            flag = [self._all_relax, ] * 3
        else:
            flag = [[self._all_relax, ]*3 for _i in range(self.natm)]
            for i in self._select_dyn:
                flag[i] = self._select_dyn[i]
        return flag

    def get_spglib_input(self):
        '''Return the input necessary for spglib to get symmetry

        Returns:
            cell (3,3), pos (n,3), index of atom type (n), with n = self.natm
        '''
        return self.latt, self.posi, self.type_index()

    # * Exporter implementations
    def export(self, output_format: str, filename=None, scale: float=1.0):
        """Export cell to file in the format `output_format`
        Args:
            output_format (str)
            filename (str or file handler) : Set None to stdout
        """
        o = output_format.lower()
        e = self.exporters.get(o, None)
        if e is None:
            raise ValueError("Unsupported export:", output_format)
        print_file_or_iowrapper(e(scale=scale), f=filename)

    def export_abi(self, scale: float = 1.0) -> str:
        """Export in ABINIT format.

        Support direct coordinates only.

        Args:
            scale (float)

        TODO:
            selective dynamic flags
        """
        syms, nats = sym_nat_from_atms(self._atms)
        ret = ["#" + self.comment,
               "acell 3*{:f} {:s}".format(scale, {"ang": "angstrom"}.get(self.unit, "")),
               "natom {:d}".format(self.natm),
               "ntypat {:d}".format(len(syms)),
               ]
        # lattice vector
        form = "rprim\n" + " {:12.8f} {:12.8f} {:12.8f}\n" * 3
        ret.append(form[:-1].format(*self._latt.flatten()))
        # nuclear charge of each atom type
        form = "znucl " + " {:d}" * len(syms)
        ret.append(form.format(*map(NUCLEAR_CHARGE.__getitem__, syms)))
        # type of each atom
        form = "typat" + " {:d}" * self.natm
        ret.append(form.format(*self.type_index(start=1)))
        # coordinates of each atom
        cwas = self.coord_sys
        self.coord_sys = "D"
        form = "xred\n" + " {:12.8f} {:12.8f} {:12.8f}\n" * self.natm
        ret.append(form[:-1].format(*self._posi.flatten()))
        if cwas == "C":
            self.coord_sys = "C"
        return "\n".join(ret)

    def export_vasp(self, scale: float = 1.0) -> str:
        """Export in VASP POSCAR format"""
        # list containting strings to return
        ret = []
        # convert to ang, as vasp use ang only
        uwas = self.unit
        self.unit = "ang"

        syms, nats = sym_nat_from_atms(self._atms)
        ret.append("{} ({})".format(self.comment, self._reference))
        ret.append("{:8.6f}".format(scale))
        for i in range(3):
            ret.append("  %12.8f  %12.8f  %12.8f"
                       % (self._latt[i, 0], self._latt[i, 1], self._latt[i, 2]))
        if not syms[0].startswith("Unk"):
            ret.append(' '.join(syms))
        ret.append(' '.join([str(x) for x in nats]))

        if self.use_select_dyn:
            ret.append("Selective Dynamics")
        ret.append({"D": "Direct", "C": "Cart"}[self._coord_sys])

        for i in range(self.natm):
            dyn = []
            if self.use_select_dyn:
                dyn = self.sd_flag(ia=i)
            ainfo = []
            if not syms[0].startswith("Unk"):
                ainfo = ['#{}'.format(self._atms[i])]
            aflag = [{True: "T", False: "F"}[d] for d in dyn] + ainfo
            ret.append("%15.9f %15.9f %15.9f " % (
                self._posi[i, 0], self._posi[i, 1], self._posi[i, 2]) + ' '.join(aflag))
        # convert back to the original length unit
        self.unit = uwas
        return '\n'.join(ret)

    def export_json(self, scale=1.0):
        """Export in JSON format"""
        raise NotImplementedError

    # * Reader implementations
    @classmethod
    def read(cls, path, form=None):
        """read file at path and return a Cell instance

        Args:
            path (str)
            form (str) : should be in avail_reader"""
        path = str(path)
        _logger.info("Reading %s", path)
        readers = {
            'vasp': cls.read_vasp,
            'cif': cls.read_cif,
            'json': cls.read_json,
            }
        try:
            if form is None:
                form = get_file_ext(path)
                if path.endswith('POSCAR'):
                    form = 'vasp'
                _logger.info("Detected format %s", form)
            return readers.get(form)(path)
        except KeyError:
            raise CellError("Unsupported reader format: {}".format(form))

    @classmethod
    def read_json(cls, pjson):
        '''Initialize a ``Cell`` instance from a JSON file

        If "factory" key does not exist, it will search for the postional arguments,
        i.e. "latt", "atoms" and "pos" keys. Raise when any of them does not exist.

        Args:
            pjson (str): the path of JSON file
        '''
        if pjson is None or not os.path.isfile(pjson):
            raise CellError("JSON file not found: {}".format(pjson))
        with open(pjson, 'r') as h:
            try:
                js = json.load(h)
            except json.JSONDecodeError:
                raise CellError("invalid JSON file for cell: {}".format(pjson))
        pargs = []
        factories = {
            "bravais_oP": (cls.bravais_oP, ("atom", "a", "b", "c")),
            "bravais_oI": (cls.bravais_oI, ("atom", "a", "b", "c")),
            "bravais_oF": (cls.bravais_oF, ("atom", "a", "b", "c")),
            "bravais_cP": (cls.bravais_cP, ("atom", "a")),
            "bravais_cI": (cls.bravais_cI, ("atom", "a")),
            "bravais_cF": (cls.bravais_cF, ("atom", "a")),
            "perovskite": (cls.perovskite, ("atom1", "atom2", "atom3", "a")),
            "zincblende": (cls.zincblende, ("atom1", "atom2", "a")),
            "diamond": (cls.diamond, ("atom", "a")),
            "wurtzite": (cls.wurtzite, ("atom1", "atom2", "a")),
            "rutile": (cls.rutile, ("atom1", "atom2", "a", "c", "u")),
            "anatase": (cls.anatase, ("atom1", "atom2", "a", "c", "u")),
            "pyrite": (cls.pyrite, ("atom1", "atom2", "a", "u")),
            "marcasite": (cls.marcasite, ("atom1", "atom2", "a", "b", "c", "v", "w")),
        }
        # found factory key
        if "factory" in js:
            fac = js["factory"]
            # pop out latt, atoms and pos for safety
            for arg in ["latt", "atms", "posi"]:
                js.pop(arg, None)
            if fac in factories:
                # get required positional argument
                try:
                    m, req_pa = factories[fac]
                    for x in req_pa:
                        pargs.append(js.pop(x))
                    return m(*pargs, **js)
                except KeyError:
                    raise CellError(
                        "Required key not found in JSON: {}".format(x))
            raise CellError("Factory method unavailable: {}".format(fac))

        for arg in ["latt", "atms", "posi"]:
            v = js.pop(arg, None)
            if v is None:
                raise CellError("invalid JSON file for cell: {}. No {}".format(pjson, arg))
            pargs.append(v)
        return cls(*pargs, **js)

    @classmethod
    def read_cif(cls, pcif):
        """Read from Cif file and return a instance by use of PyCIFRW
        """
        cif = Cif(pcif)
        kw = {"coord_sys": "D", "reference": cif.get_reference_str(), }
        # use chemical name as comment
        kw['comment'] = ', '.join(cif.get_chemical_name()) + ' type'
        latt = cif.get_lattice_vectors()
        atms, posi = cif.get_all_atoms()
        return cls(latt, atms, posi, **kw)

    # pylint: disable=R0914,R0915
    @classmethod
    def read_vasp(cls, pvasp="./POSCAR"):
        """Create Cell instance by reading from vasp POSCAR file

        Args:
            pvasp (str) : path to vasp POSCAR file, default to POSCAR at cwd
        """
        def _raise_errline(cond, i=None, s="input"):
            if cond:
                if i:
                    raise CellError("bad {:s}, atom L{} in file {:s}".format(s, i+1, pvasp))
                raise CellError("bad {:s} in file {:s}".format(s, pvasp))

        fixed = {}
        flags = {'T': True, 'F': False}
        with open(pvasp, 'r') as fp:
            symbols = None
            # line 1: comment on system
            comment = fp.readline().strip()
            # line 2: scale
            scale = float(fp.readline().strip())
            # line 3-5: lattice vector
            latt = [fp.readline().split() for _ in range(3)]
            latt = np.array(latt, dtype='float64') * scale
            # Next 2 or 1 line(s), depend on whether element symbols are typed or not
            _line = fp.readline().strip()
            if _line[0] in string.ascii_letters:
                symbols = _line.split()
                _line = fp.readline().strip()
            _raise_errline(_line[0] not in string.digits[1:], s="atomic format")
            nats = [int(x) for x in _line.split()]
            if symbols is None:
                _logger.warning("No atom information in POSCAR: %s", pvasp)
                potcar_info = grep("VRHFIN", os.path.join(os.path.dirname(pvasp), "POTCAR"))
                if potcar_info is not None:
                    symbols = [x.split("=")[1].split(":")[0] for x in potcar_info]
                    _logger.info("got symbols from POTCAR in same directory")
                    _logger.info(">> %r", symbols)
                else:
                    symbols = ["Unk{}".format(i) for i, _ in enumerate(nats)]
            atms = atms_from_sym_nat(symbols, nats)

            # Next 2 or 1 line(s), depend on whether 'selective dynamics line' is typed
            _line = fp.readline().strip()
            if _line[0].upper() == "S":
                _line = fp.readline().strip()
            coord = _line[0].upper()
            _raise_errline(coord not in ["C", "K", "D"], s="coord system")
            coord = {"C": "C", "K": "C", "D": "D"}[coord]

            # Next natms lines: read atomic position and selective dynamics flag
            posi = []
            scale = {"C": scale}.get(coord, 1.0E0)
            _atms_posline = []
            for i in range(sum(nats)):
                # read positions
                try:
                    _words = trim_comment(fp.readline()).split()
                    posi.append(_words[:3])
                except (ValueError, IndexError):
                    _raise_errline(True, i, "coordinates")
                ncols = len(_words)
                if ncols == 3:
                    continue
                # read possible selective dynamic flags, and atom type
                # add possible atomic info for ATAT-like POSCAR
                if ncols in [4, 7]:
                    _atms_posline.append(_words[-1])
                elif ncols == 6:
                    flag = [flags.get(_words[i]) for i in range(3, 6)]
                    _raise_errline(None in flag, i, "flag")
                    if flag != [True, True, True]:
                        fixed[i] = flag
                else:
                    _raise_errline(True, i, "poscar line")
            posi = np.array(posi, dtype='float64') * scale
            if _atms_posline:
                atms = _atms_posline
            return cls(latt, atms, posi, unit="ang", coord_sys=coord,
                       all_relax=True, select_dyn=fixed, comment=comment)


    # * Factory methods
    @classmethod
    def _bravais_o(cls, kind, atom, a, b, c, **kwargs):
        assert kind in ["P", "I", "F"]
        latt = [[a, 0.0, 0.0], [0.0, b, 0.0], [0.0, 0.0, c]]
        if kind == "P":
            atms = [atom, ]
            posi = [[0.0, 0.0, 0.0]]
        if kind == "I":
            atms = [atom, ]*2
            posi = [[0.0, 0.0, 0.0], [0.5, 0.5, 0.5]]
        if kind == "F":
            atms = [atom, ]*4
            posi = [[0.0, 0.0, 0.0], [0.0, 0.5, 0.5],
                    [0.5, 0.0, 0.5], [0.5, 0.5, 0.0]]
        kwargs.pop("coord_sys", None)
        return cls(latt, atms, posi, **kwargs)

    @classmethod
    def bravais_oP(cls, atom, a=1.0, b=2.0, c=3.0, **kwargs):
        '''Generate a simple orthorhombic Bravais lattice

        Args:
            atom (str) : the chemical symbol of atom
            a,b,c (float) : the lattice constants (a,b,c)
            kwargs: keyword argument for ``Cell`` except ``coord_sys``
        '''
        if "comment" not in kwargs:
            kwargs.update(
                {"comment": "Simple orthorhombic lattice {}".format(atom)})
        return cls._bravais_o("P", atom, a, b, c, **kwargs)

    @classmethod
    def bravais_oI(cls, atom, a=1.0, b=2.0, c=3.0, **kwargs):
        '''Generate a body-centered orthorhombic Bravais lattice

        Args:
            atom (str) : the chemical symbol of atom
            a,b,c (float) : the lattice constants (a,b,c)
            kwargs: keyword argument for ``Cell`` except ``coord_sys``
        '''
        if "comment" not in kwargs:
            kwargs.update(
                {"comment": "Body-centered orthorhombic lattice {}".format(atom)})
        return cls._bravais_o("I", atom, a, b, c, **kwargs)

    @classmethod
    def bravais_oF(cls, atom, a=1.0, b=2.0, c=3.0, **kwargs):
        '''Generate a face-centered orthorhombic Bravais lattice

        Args:
            atom (str) : the chemical symbol of atom
            a,b,c (float) : the lattice constants (a,b,c)
            kwargs: keyword argument for ``Cell`` except ``coord_sys``
        '''
        if "comment" not in kwargs:
            kwargs.update(
                {"comment": "Face-centered orthorhombic lattice {}".format(atom)})
        return cls._bravais_o("F", atom, a, b, c, **kwargs)

    @classmethod
    def bravais_cP(cls, atom, a=1.0, **kwargs):
        '''Generate a simple cubic Bravais lattice, space group 221

        Args:
            atom (str) : the chemical symbol of atom
            a (float) : the lattice constant (a)
            kwargs: keyword argument for ``Cell`` except ``coord_sys``
        '''
        _a = abs(a)
        latt = [[_a, 0.0, 0.0], [0.0, _a, 0.0], [0.0, 0.0, _a]]
        atms = [atom,]
        posi = [[0.0, 0.0, 0.0]]
        kwargs.pop("coord_sys", None)
        if "comment" not in kwargs:
            kwargs.update({"comment": "Simple cubic lattice {}".format(atom)})
        return cls(latt, atms, posi, **kwargs)

    @classmethod
    def bravais_cI(cls, atom, a=1.0, primitive=False, **kwargs):
        '''Generate a body-centered cubic Bravais lattice

        Args:
            atom (str) : the chemical symbol of atom
            a (float) : the lattice constant (a)
            primitive (bool) : if set True, the primitive cell will be generated
            kwargs: keyword argument for ``Cell`` except ``coord_sys``
        '''
        _a = abs(a)
        if primitive:
            latt = [[-_a/2.0, _a/2.0, _a/2.0],
                    [_a/2.0, -_a/2.0, _a/2.0],
                    [_a/2.0, _a/2.0, -_a/2.0]]
            atms = [atom]
            posi = [[0.0, 0.0, 0.0]]
        else:
            latt = [[_a, 0.0, 0.0], [0.0, _a, 0.0], [0.0, 0.0, _a]]
            atms = [atom, ]*2
            posi = [[0.0, 0.0, 0.0], [0.5, 0.5, 0.5]]
        kwargs.pop("coord_sys", None)
        if "comment" not in kwargs:
            kwargs.update({"comment": "BCC {}".format(atom)})
        return cls(latt, atms, posi, **kwargs)

    @classmethod
    def bravais_cF(cls, atom, a=1.0, primitive=False, **kwargs):
        '''Generate a face-centered cubic Bravais lattice

        Args:
            atom (str) : the chemical symbol of atom
            a (float) : the lattice constant (a)
            primitive (bool) : if set True, the primitive cell will be generated
            kwargs: keyword argument for ``Cell`` except ``coord_sys``
        '''
        _a = abs(a)
        if primitive:
            latt = [[0.0, _a/2.0, _a/2.0],
                    [_a/2.0, 0.0, _a/2.0], [_a/2.0, _a/2.0, 0.0]]
            atms = [atom]
            posi = [[0.0, 0.0, 0.0]]
        else:
            latt = [[_a, 0.0, 0.0], [0.0, _a, 0.0], [0.0, 0.0, _a]]
            atms = [atom,]*4
            posi = [[0.0, 0.0, 0.0], [0.0, 0.5, 0.5],
                    [0.5, 0.0, 0.5], [0.5, 0.5, 0.0]]
        kwargs.pop("coord_sys", None)
        if "comment" not in kwargs:
            kwargs.update({"comment": "FCC {}".format(atom)})
        return cls(latt, atms, posi, **kwargs)

    @classmethod
    def perovskite(cls, atom1="Ca", atom2="Ti", atom3="O", a=1.0, **kwargs):
        '''Generate a perovskit lattice

        Args:
            atom1 (str) : the chemical symbol of atom at vertices of cubic cell
            atom2 (str) : the chemical symbol of atom at center of cubic cell
            atom3 (str) : the chemical symbol of atom at faces of cubic cell
            a (float) : the lattice constant (a)
            primitive (bool) : if set True, the primitive cell will be generated
            kwargs: keyword argument for ``Cell`` except ``coord_sys``
        '''
        _a = abs(a)
        latt = [[_a, 0.0, 0.0], [0.0, _a, 0.0], [0.0, 0.0, _a]]
        atms = [atom1, atom2, ] + [atom3, ]*3
        posi = [[0.0, 0.0, 0.0], [0.5, 0.5, 0.5], [
            0.0, 0.5, 0.5], [0.5, 0.0, 0.5], [0.5, 0.5, 0.0]]
        kwargs.pop("coord_sys", None)
        if "comment" not in kwargs:
            kwargs.update(
                {"comment": "Perovskite {}{}{}3".format(atom1, atom2, atom3)})
        return cls(latt, atms, posi, **kwargs)

    @classmethod
    def zincblende(cls, atom1="Zn", atom2="O", a=1.0, primitive=False, **kwargs):
        '''Generate a zincblende lattice (space group 216)

        ``atom1`` are placed at vertex and ``atom2`` at tetrahedron interstitial

        Args:
            atom1 (str): symbol of atom at vertex
            atom2 (str): symbol of atom at tetrahedron interstitial
            a (float): the lattice constant of the conventional cell.
            primitive (bool): if set True, the primitive cell will be generated.
            kwargs: keyword argument for ``Cell`` except ``coord_sys``
        '''
        _a = abs(a)
        if primitive:
            latt = [[0.0, _a/2.0, _a/2.0],
                    [_a/2.0, 0.0, _a/2.0], [_a/2.0, _a/2.0, 0.0]]
            atms = [atom1, atom2]
            posi = [[0.0, 0.0, 0.0],
                    [0.25, 0.25, 0.25]]
        else:
            latt = [[_a, 0.0, 0.0], [0.0, _a, 0.0], [0.0, 0.0, _a]]
            atms = [atom1, ]*4 + [atom2, ]*4
            posi = [[0.0, 0.0, 0.0],
                    [0.0, 0.5, 0.5],
                    [0.5, 0.0, 0.5],
                    [0.5, 0.5, 0.0],
                    [0.25, 0.25, 0.25],
                    [0.25, 0.75, 0.75],
                    [0.75, 0.25, 0.75],
                    [0.75, 0.75, 0.25]]
        kwargs.pop("coord_sys", None)
        if "comment" not in kwargs:
            kwargs.update({"comment": "Zincblende {}{}".format(atom1, atom2)})
        return cls(latt, atms, posi, **kwargs)

    @classmethod
    def rocksalt(cls, atom1="Na", atom2="Cl", a=1.0, primitive=False, **kwargs):
        '''Generate a rocksalt lattice

        ``atom1`` are placed at vertex and ``atom2`` at tetrahedron interstitial

        Args:
            atom1 (str): symbol of atom1 (set at vertex)
            atom2 (str): symbol of atom2
            a (float): the lattice constant of the conventional cell.
            primitive (bool): if set True, the primitive cell will be generated.
            kwargs: keyword argument for ``Cell`` except ``coord_sys``
        '''
        _a = abs(a)
        if primitive:
            latt = [[0.0, _a/2.0, _a/2.0],
                    [_a/2.0, 0.0, _a/2.0],
                    [_a/2.0, _a/2.0, 0.0]]
            atms = [atom1, atom2]
            posi = [[0.0, 0.0, 0.0],
                    [0.5, 0.5, 0.5]]
        else:
            latt = [[_a, 0.0, 0.0], [0.0, _a, 0.0], [0.0, 0.0, _a]]
            atms = [atom1, ]*4 + [atom2, ]*4
            posi = [[0.0, 0.0, 0.0],
                    [0.0, 0.5, 0.5],
                    [0.5, 0.0, 0.5],
                    [0.5, 0.5, 0.0],
                    [0.5, 0.0, 0.0],
                    [0.0, 0.5, 0.0],
                    [0.0, 0.0, 0.5],
                    [0.5, 0.5, 0.5]]
        kwargs.pop("coord_sys", None)
        if "comment" not in kwargs:
            kwargs.update({"comment": "Rocksalt {}{}".format(atom1, atom2)})
        return cls(latt, atms, posi, **kwargs)
        
    @classmethod
    def diamond(cls, atom="C", a=1.0, primitive=False, **kwargs):
        '''Generate a diamond lattice (space group 227)

        Args:
            atom (str): symbol of the atom
            a (float): the lattice constant of the conventional cell.
            primitive (bool): if set True, the primitive cell will be generated.
            kwargs: keyword argument for ``Cell`` except ``coord_sys``
        '''
        if "comment" not in kwargs:
            kwargs.update({"comment": "Diamond {}".format(atom)})
        return cls.zincblende(atom, atom, a=a, primitive=primitive, **kwargs)

    @classmethod
    def wurtzite(cls, atom1="Zn", atom2="O", a=3.250, c=None, u=None, **kwargs):
        '''Generate a wurtzite lattice (space group 186)

        Args:
            atom1 (str): symbol of atom at vertices of lattice
            atom2 (str): symbol of atom at edges of lattice
            a, c (float): the lattice constant of the cell.
            u (float): internal coordinate, > 0.25
            kwargs: keyword argument for ``Cell`` except ``coord_sys``
        '''
        a = abs(a)
        halfa = a/2.0
        if c is None:
            c = a * np.sqrt(8.0/3)
        if u is None:
            u = 1.0/6
        latt = [[a, 0.0, 0.0],
                [-halfa, np.sqrt(3)*halfa, 0.0],
                [0.0, 0.0, c]]
        atms = [atom1, ]*2 + [atom2, ]*2
        posi = [[0.0, 0.0, 0.0],
                [2.0/3, 1.0/3, 0.5],
                [0.0, 0.0, 1.0-u],
                [2.0/3, 1.0/3, 0.5-u]]
        kwargs.pop("coord_sys", None)
        if "comment" not in kwargs:
            kwargs.update({"comment": "Wurtzite {}{}".format(atom1, atom2)})
        return cls(latt, atms, posi, **kwargs)

    @classmethod
    def rutile(cls, atom1="Ti", atom2="O", a=1.0, c=2.0, u=0.31, **kwargs):
        '''Generate a rutile lattice (space group 136)

        Args:
            atom1 (str): symbol of atom at vertex and center of lattice
            atom2 (str): symbol of atom at face of lattice
            a,c (float): the lattice constant of the cell.
            u (float): the internal coordinate
            kwargs: keyword argument for ``Cell`` except ``coord_sys``
        '''
        try:
            assert 0.0 < u < 1.0
        except AssertionError:
            raise cls._err(
                "Internal coordinate should be in (0,1), get {}".format(u))
        _a = abs(a)
        _c = abs(c)
        latt = [[_a, 0.0, 0.0], [0.0, _a, 0.0], [0.0, 0.0, _c]]
        atms = [atom1, ]*2 + [atom2, ]*4
        posi = [[0.0, 0.0, 0.0],
                [0.5, 0.5, 0.5],
                [u, u, 0.0],
                [-u, -u, 0.0],
                [0.5-u, 0.5+u, 0.5],
                [0.5+u, 0.5-u, 0.5]]
        kwargs.pop("coord_sys", None)
        if "comment" not in kwargs:
            kwargs.update({"comment": "Rutile {}{}2".format(atom1, atom2)})
        return cls(latt, atms, posi, **kwargs)

    @classmethod
    def anatase(cls, atom1="Ti", atom2="O", a=3.7845, c=9.5143, u=0.2199,
                primitive=False, **kwargs):
        '''Generate an anatase lattice (space group 141).

        Note:
            This cell is not standardized.

        Args:
            atom1 (str): symbol of atom at vertex
            atom2 (str): symbol of atom at face of lattice
            a,c (float): the lattice constant of the conventional cell.
            u (float): the internal coordinate, i.e. distance between two atoms in terms of c
            kwargs: keyword argument for ``Cell`` except ``coord_sys``
        '''
        try:
            assert 0.0 < u < 1.0
        except AssertionError:
            raise cls._err(
                "Internal coordinate should be in (0,1), get {}".format(u))
        _a = abs(a)
        _c = abs(c)
        if primitive:
            latt = [[-_a/2, _a/2, _c/2],
                    [_a/2, -_a/2, _c/2], [_a/2, _a/2, -_c/2]]
            atms = [atom1, ]*2 + [atom2, ]*4
            posi = [[0.0, 0.0, 0.0],
                    [0.75, 0.25, 0.5],
                    [0.25-u, 0.75-u, 0.5],
                    [0.25+u, 0.75+u, 0.5],
                    [0.5+u,  0.5+u, 0.0],
                    [0.5-u,  0.5-u, 0.0], ]
        else:
            latt = [[_a, 0.0, 0.0], [0.0, _a, 0.0], [0.0, 0.0, _c]]
            atms = [atom1, ]*4 + [atom2, ]*8
            posi = [[0.0, 0.0, 0.0],
                    [0.5, 0.0, 0.25],
                    [0.0, 0.5, 0.75],
                    [0.5, 0.5, 0.5],
                    [0.0, 0.0,   u],
                    [0.0, 0.0,  -u],
                    [0.5, 0.0, 0.25-u],
                    [0.5, 0.0, 0.25+u],
                    [0.0, 0.5, 0.75-u],
                    [0.0, 0.5, 0.75+u],
                    [0.5, 0.5, 0.5-u],
                    [0.5, 0.5, 0.5+u]]
        kwargs.pop("coord_sys", None)
        if "comment" not in kwargs:
            kwargs.update({"comment": "Anatase {}{}2".format(atom1, atom2)})
        return cls(latt, atms, posi, **kwargs)

    @classmethod
    def pyrite(cls, atom1="Fe", atom2="S", a=5.4183, u=0.1174, **kwargs):
        '''Generate a standardized pyrite lattice (space group 205).

        Args:
            atom1 (str): symbol of atom at vertex and face-center
            atom2 (str): symbol of atom at edges
            a (float): the lattice constant of the conventional cell.
            u (float): the internal coordinate
            kwargs: keyword argument for ``Cell`` except ``coord_sys``
        '''
        _a = abs(a)
        latt = [[_a, 0.0, 0.0], [0.0, _a, 0.0], [0.0, 0.0, _a]]
        atms = [atom1, ]*4 + [atom2, ]*8
        posi = [[0.0, 0.0, 0.0],
                [0.0, 0.5, 0.5],
                [0.5, 0.0, 0.5],
                [0.5, 0.5, 0.0],
                [0.5-u,     u,    -u],
                [0.5+u,    -u,     u],
                [-u, 0.5-u,     u],
                [u, 0.5+u,    -u],
                [u,    -u, 0.5-u],
                [-u,     u, 0.5+u],
                [0.5+u, 0.5+u, 0.5+u],
                [0.5-u, 0.5-u, 0.5-u]]
        kwargs.pop("coord_sys", None)
        if "comment" not in kwargs:
            kwargs.update({"comment": "Pyrite {}{}2".format(atom1, atom2)})
        return cls(latt, atms, posi, **kwargs)

    @classmethod
    def marcasite(cls, atom1="Fe", atom2="S",
                  a=4.4450, b=5.4151, c=3.3922,
                  v=0.2066, w=0.3750, **kwargs):
        '''Generate a standardized marcasite lattice (space group 58).

        Args:
            atom1 (str): symbol of atom at vertex and body-center
            atom2 (str): symbol of the other atom
            a, b, c (float): the lattice constants of the cell.
            v, w(float): the internal coordinates
            kwargs: keyword argument for ``Cell`` except ``coord_sys``
        '''
        _a = abs(a)
        _b = abs(b)
        _c = abs(c)
        latt = [[_a, 0.0, 0.0], [0.0, _b, 0.0], [0.0, 0.0, _c]]
        atms = [atom1, ]*2 + [atom2, ]*4
        posi = [[0.0, 0.0, 0.0],
                [0.5, 0.5, 0.5],
                [0.5+v, 0.5-w,    0.5],
                [0.5-v, 0.5+w,    0.5],
                [-v,    -w,    0.0],
                [v,     w,    0.0], ]
        kwargs.pop("coord_sys", None)
        if "comment" not in kwargs:
            kwargs.update({"comment": "Marcasite {}{}2".format(atom1, atom2)})
        return cls(latt, atms, posi, **kwargs)

