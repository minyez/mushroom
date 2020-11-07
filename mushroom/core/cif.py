# -*- coding: utf-8 -*-
"""this module defines the object to process .cif files"""
import os
import re
import CifFile

from mushroom.core.crystutils import get_latt_vecs_from_latt_consts, get_all_atoms_from_symops
from mushroom.core.data import conv_estimate_number, closest_frac
from mushroom.core.logger import create_logger

_logger = create_logger("cif")
del create_logger

class Cif:
    """Class to read CIF files and initialize atomic data by PyCIFRW

    Args:
        pcif (str): the path to cif file
    """

    def __init__(self, pcif):
        if not os.path.isfile(pcif):
            raise FileNotFoundError(pcif)
        # data block
        self._blk = CifFile.ReadCif(pcif, scantype="flex").first_block()
        self.__init_inequiv()
        self.__init_symmetry_operations()
        self._latt = None
        self.atms = None
        self.posi = None
        self.ref = None

    @property
    def latt(self):
        return self.get_lattice_vectors()

    def __init_inequiv(self):
        """initialize the positions and symbols of all inequivalent atoms"""
        posi_ineq = []
        atms_ineq = []
        natoms_per_ineq = []
        for l in self._blk.GetLoop("_atom_site_fract_x"):
            posOne = []
            for a in ["_atom_site_fract_x", "_atom_site_fract_y", "_atom_site_fract_z"]:
                p = conv_estimate_number(l.__getattribute__(a))
                # deal with approximate value of fractions
                _logger.debug("read %s: %s", a, p)
                try:
                    p = closest_frac(p, maxn=20)
                except ValueError:
                    pass
                _logger.debug("cloest fraction: %s", p)
                posOne.append(p)
            posi_ineq.append(posOne)
            natoms_per_ineq.append(int(l._atom_site_symmetry_multiplicity))
            # remove chemical valence
            atms_ineq.append(re.sub(r"[\d]+[+-]?", "", l._atom_site_type_symbol))
        self.posi_ineq = posi_ineq
        self.atms_ineq = atms_ineq
        self.natm_ineq = natoms_per_ineq

    def __init_symmetry_operations(self):
        """get all symmetry operations"""
        self.operations = {}
        rots = []
        trans = []
        try:
            symmetry_key = "_symmetry_equiv_pos_as_xyz" 
            symmetry_loop = self._blk.GetLoop(symmetry_key)
        except KeyError:
            symmetry_key = "_space_group_symop_operation_xyz"
            symmetry_loop = self._blk.GetLoop(symmetry_key)

        for l in symmetry_loop:
            r, t = decode_equiv_pos_string(l.__getattribute__(symmetry_key))
            rots.append(r)
            trans.append(t)
        self.operations["rotations"] = tuple(rots)
        self.operations["translations"] = tuple(trans)

    def get_chemical_name(self):
        """Return the chemical names stored in the head of a CIF file

        Returns
            3 str, systematic name, mineral name and structure type
        """
        sys = None
        sys_keys = ["_chemical_name_systematic", "_chemical_name_common", "_chemical_formula_sum"]
        for k in sys_keys:
            try:
                sys = self._blk.GetItemValue(k)
                continue
            except KeyError:
                pass
        if sys is None:
            sys = "NA"
        try:
            mine = self._blk.GetItemValue("_chemical_name_mineral")
        except KeyError:
            mine = "NA"
        try:
            struct = self._blk.GetItemValue("_chemical_name_structure_type")
        except KeyError:
            struct = "NA"
        return sys, mine, struct

    def get_lattice_vectors(self):
        """initialize the lattice vectors from cif

        Returns
            list, shape (3,3)
        """
        if self._latt is None:
            latta, lattb, lattc = tuple(
                map(
                    lambda x: conv_estimate_number(self._blk.GetItemValue(x)),
                    ["_cell_length_a", "_cell_length_b", "_cell_length_c"],
                )
            )
            angles = []
            for a in ["_cell_angle_alpha", "_cell_angle_beta", "_cell_angle_gamma"]:
                angles.append(conv_estimate_number(self._blk.GetItemValue(a)))
            _logger.debug("found angles: %r", angles)
            self._latt = get_latt_vecs_from_latt_consts(latta, lattb, lattc, *angles)
        _logger.debug("lattice parameters: %r", self._latt)
        return self._latt

    def get_all_atoms(self):
        """return the symbols and positions of all atoms
        by performing symmetry operations on all inequivalent atoms

        Returns:
            two list, symbols and positions of all atoms, 
            shape (n,) and (n,3) with n the total number of atoms
        """
        if self.atms is None or self.posi is None:
            atms, posi = get_all_atoms_from_symops(
                self.atms_ineq, self.posi_ineq, self.operations, latt=self.latt)
            # consistency check
            _logger.debug("natoms of each inequiv type: %r", self.natm_ineq)
            _logger.debug("positions of each inequiv type: %r", self.posi_ineq)
            _logger.debug("number of all atoms: %r", len(atms))
            if sum(self.natm_ineq) != len(atms):
                raise ValueError(
                    "inconsistent number of atoms and entries after symmetry operations:",
                    sum(self.natm_ineq), len(atms)
                )
            self.atms = atms
            self.posi = posi
        return self.atms, self.posi

    def get_reference_str(self):
        """Get the reference string

        Returns:
            str, empyt string if no reference is found in the cif file
        """
        if self.ref is None:
            try:
                ref = map(lambda x: self._blk.GetItemValue(x)[0], ["_citation_journal_full",
                                                                   "_citation_journal_volume",
                                                                   "_citation_page_first"])
                ref = "{} vol {}, pp {}".format(*ref)
            except KeyError:
                ref = ""
            self.ref = ref.replace('\n', ' ')
        return self.ref

def decode_equiv_pos_string(s):
    """Convert a string representing symmetry operation in CIF file
    to a rotation matrix R and a translation vector t

    The relation between original and transformed fractional coordinate, x and x',
    is

    x' = Rx + t

    Obviously, x, x' and t are treated as a column vector

    Args:
        s (str): a symmetry operation string found in 
            _symmetry_equiv_pos_as_xyz item of a CIF file.

    Returns:
        two lists, shape (3,3) and (3,)
    """
    trans = [0, 0, 0]
    rot = [[0, 0, 0], [0, 0, 0], [0, 0, 0]]
    items = [x.strip() for x in s.split(",")]
    if len(items) != 3:
        raise ValueError("s does not seem to be a symmetry operation string")
    for i in items:
        if len(i) == 0:
            raise ValueError("s does not seem to be a symmetry operation string")

    d = {"x": 0, "y": 1, "z": 2}
    for i in range(3):
        stList = items[i].split("+")
        for st in stList:
            # loop in case that string like '-x-y' appears
            while True:
                sign = 1
                try:
                    if st.startswith("-"):
                        sign = -1
                        st = st[1:]
                    if st[0] in d:
                        rot[i][d[st[0]]] = sign
                        st = st[1:]
                    else:
                        # confront number
                        break
                except IndexError:
                    # end of line
                    break
            if len(st) == 0:
                continue
            # deal with fractional number x/y
            trans[i] = float(st[0]) / float(st[-1])
    return rot, trans


