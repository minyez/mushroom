# -*- coding: utf-8 -*-
"""this module defines the object to process .cif files"""
import os
import re
import CifFile

from mushroom.core.crystutils import get_latt_vecs_from_latt_consts, get_all_atoms_from_sym_ops
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
        self.latt = None
        self.atms = None
        self.posi = None
        self.ref = None

    def __init_inequiv(self):
        """initialize the positions and symbols of all inequivalent atoms"""
        posi_ineq = []
        atms_ineq = []
        natomsPerInequiv = []
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
            natomsPerInequiv.append(int(l._atom_site_symmetry_multiplicity))
            # remove chemical valence
            atms_ineq.append(re.sub(r"[\d]+[+-]?", "", l._atom_site_type_symbol))
        self.posi_ineq = posi_ineq
        self.atms_ineq = atms_ineq
        self.natm_ineq = natomsPerInequiv

    def __init_symmetry_operations(self):
        """get all symmetry operations"""
        self.operations = {}
        rots = []
        trans = []
        for l in self._blk.GetLoop("_symmetry_equiv_pos_site_id"):
            r, t = Cif.decode_equiv_pos_string(l._symmetry_equiv_pos_as_xyz)
            rots.append(r)
            trans.append(t)
        self.operations["rotations"] = tuple(rots)
        self.operations["translations"] = tuple(trans)

    def get_chemical_name(self):
        """Return the chemical names stored in the head of a CIF file

        Returns
            3 str, systematic name, mineral name and structure type
        """
        try:
            sys = self._blk.GetItemValue("_chemical_name_systematic")
        except KeyError:
            sys = "NA"
        try:
            mine = self._blk.GetItemValue("_chemical_name_mineral")
        except KeyError:
            mine = "NA"
        try:
            struct = self._blk.GetItemValue("_chemical_name_structure_type")
        except (KeyError, ValueError):
            struct = "NA"
        return sys, mine, struct

    def get_lattice_vectors(self):
        """initialize the lattice vectors from cif

        Returns
            list, shape (3,3)
        """
        if self.latt is None:
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
            self.latt = get_latt_vecs_from_latt_consts(latta, lattb, lattc, *angles)
        _logger.debug("lattice parameters: %r", self.latt)
        return self.latt

    def get_all_atoms(self):
        """return the symbols and positions of all atoms
        by performing symmetry operations on all inequivalent atoms

        Returns:
            two list, symbols and positions of all atoms, 
            shape (n,) and (n,3) with n the total number of atoms
        """
        if self.atms is None or self.posi is None:
            atms, posi = get_all_atoms_from_sym_ops(
                self.atms_ineq, self.posi_ineq, self.operations)
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
                ref = "".join(self._blk.GetItemValue("_publ_section_title").split("\n"))
            except KeyError:
                ref = ""
            self.ref = ref
        return self.ref

    @staticmethod
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


