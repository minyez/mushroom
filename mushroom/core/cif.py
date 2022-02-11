# -*- coding: utf-8 -*-
"""this module defines the object to process .cif files"""
# pylint: disable=C0209,W1514
import os
import re
from typing import List
from io import StringIO
try:
    import CifFile
except ImportError:
    CifFile = None

from mushroom.core.crystutils import get_latt_vecs_from_latt_consts, get_all_atoms_from_symops
from mushroom.core.ioutils import raise_no_module, open_textio
from mushroom.core.data import conv_estimate_number, closest_frac
from mushroom.core.logger import create_logger

_logger = create_logger("cif")
del create_logger

class _CifFile:
    """
    Object to handle the file conforming the format of crystallographic information file (CIF)

    This includes parsing loops and values by reading file (read class method)
    and dump data to file (write method)

    About the structure of a CIF file.
    Each CIF file can contain several data blocks. Each block starts with a string like 'data_xxxx'.
    Data are stored in items, standing individually or in loop.
    The item name must starts with an underscore.

    The loop starts with a single 'loop_', followed by names of containing items, each as a line.
    The first line that does not start with an underscore is treated
    as the start of the data entries. The data entries stops at a new line, loop or item.

    This object is intended to replace the external CifFile object.
    The main reason is to remove the PyCIFRW dependency.
    """
    def __init__(self, *blks):
        self._blks = blks

    def get_blk(self, iblk):
        """get the data block"""
        return self._blks[iblk]

    def first_block(self):
        """return the first data block"""
        return self._blks[0]

    @property
    def nblk(self):
        """number of data blocks"""
        return len(self._blks)

    def export(self):
        """export the content as a string"""
        raise NotImplementedError

    def write(self, pcif):
        """write the CIF content to a file"""
        with open(pcif, 'w') as _h:
            print(self.export(), file=_h)

    @classmethod
    def build(cls, name: str, items: dict, loops: List[dict]):
        """create a CIF object containing single data block

        See CifBlk object for the arguments
        """
        blk = _CifBlk(name, items, loops)
        return cls(blk)

    @classmethod
    def read(cls, pcif):
        """read the CIF file"""
        with open_textio(pcif) as h:
            lines = h.readlines()
        # search data block
        blks_st = [i for i, l in enumerate(lines) if l.startswith("data_")]
        blks = [_CifBlk.read(StringIO(''.join(lines[st:blks_st[i+1]])))
                for i, st in enumerate(blks_st[:-1])]
        blks.append(_CifBlk.read(StringIO(''.join(lines[blks_st[-1]:]))))
        return cls(*blks)

class _CifBlk:
    """Object to handle CIF data block

    Each block is a dict, containing three keys:
        name: a string, charactering the data block
        items: a dict, the simple key-value pair in CIF
        loops: a list, each member is a dict containing "keys" (a list) and "values" (list of lists)
            the member of values list is one entry containing data corresponding to "keys".
    """
    def __init__(self, name: str, items: dict, loops: List[dict]):
        self._name = name
        self._items = items
        self._loops = loops

    @property
    def name(self):
        """the name of the data block"""
        return self._name

    def get_item(self, key):
        """get the value of an item.

        Returns:
            str, if the key is found in item
            a tuple of str, if the key is found in the loops
        """
        v = self._items.get(key, None)
        if v is None:
            for loop in self._loops:
                if key in loop["keys"]:
                    i = loop["keys"].index(key)
                    return tuple(e[i] for e in loop["values"])
        else:
            return v
        raise KeyError(f"key {key} is not found in items or loops")

    def get_loop(self, key):
        """get the loop structure where the key lives

        Returns:
            an iterator
        """
        for loop in self._loops:
            if key in loop["keys"]:
                for entry in len(loop["values"]):
                    d = dict(zip(loop["keys"], entry))
                    yield d

    @property
    def items(self):
        """items"""
        return self._items

    @property
    def loops(self):
        """loop data"""
        return self._loops

    # pylint: disable=R0912,R0914,R0915
    @classmethod
    def read(cls, pcifblk):
        """read the CIF block"""
        with open_textio(pcifblk) as h:
            # strip and filter empty lines
            lines = [l.strip() for l in h.readlines() if l and not l.startswith("#")]

        def _handle_multiline_value(st):
            """st: the line index containing the starting semicolon"""
            _l = lines[st]
            # if the first column is a keyword ("_"), remove it since we only need value
            if _l.startswith("_"):
                _, _l = _l.split(maxsplit=1)
            assert _l.startswith(";")
            _l = "\"" + _l.lstrip(";")
            if len(_l) > 1:
                _l = _l + " "
            _lines = [_l,]
            ed = st + 1
            while ed < len(lines):
                _lines.append(lines[ed] + " ")
                if lines[ed].startswith(";"):
                    break
                ed += 1
            _lines[-1] = "\"" + _lines[-1].lstrip(";")
            return ed, "".join(_lines)

        name = lines[0].lstrip('data_')
        items = {}
        loops = []
        i = 1

        while i < len(lines):
            l = lines[i]
            _logger.debug("handling line %d: %s", i, l.rstrip())
            # items
            if l.startswith("_"):
                try:
                    k, v = l.split(maxsplit=1)
                    if v.startswith(";"):
                        i, v = _handle_multiline_value(i)
                except ValueError:
                    k = l
                    i += 1
                    if v.startswith(";"):
                        i, v = _handle_multiline_value(i+1)
                    else:
                        v = l
                items[k] = v
                _logger.info("cif item %s = %s", k, v)
                i += 1
            # items defined in a loop
            elif l.startswith("loop_"):
                loop = {"keys": [], "values": []}
                i += 1
                # read in keys
                while True:
                    try:
                        l = lines[i]
                    except IndexError:
                        break
                    if l.startswith("_"):
                        loop["keys"].append(l)
                        _logger.info("loop key %s", l)
                        i += 1
                    else:
                        break
                # read in data
                nkeys = len(loop["keys"])
                datastr = ""
                in_multiline = False
                while not (l.startswith("_") or l.startswith("data_") or l.startswith("loop_")):
                    if l.startswith(";"):
                        l = " \"" + l[1:]
                        # exiting multi-line environment
                        if in_multiline:
                            l = l[1:]
                        in_multiline = not in_multiline
                    else:
                        l = " " + l
                    datastr += l
                    i += 1
                    try:
                        l = lines[i]
                    except IndexError:
                        break
                _logger.debug("handling loop data string: %s", datastr)
                m = [g.group().strip("\'\"")
                     for g in re.finditer(r'([\'\"])?(?(1).*?\1|\S+)', datastr)]
                nentries = len(m) // nkeys
                for ie in range(nentries):
                    loop["values"].append(m[nkeys*ie:nkeys*(ie+1)])
                loops.append(loop)
                _logger.info("loaded %d loop data, in %d entries", len(m), nentries)
        return cls(name, items, loops)

class Cif:
    """Class to read CIF files and initialize atomic data by PyCIFRW

    Args:
        pcif (str): the path to cif file
    """

    def __init__(self, pcif, scantype="flex"):
        if not os.path.isfile(pcif):
            raise FileNotFoundError(pcif)
        raise_no_module(CifFile, "PyCIFRW", "CifFile")
        # data block
        self._blk = CifFile.ReadCif(pcif, scantype=scantype).first_block()
        self.__init_inequiv()
        self.__init_symmetry_operations()
        self._latt = None
        self.atms = None
        self.posi = None
        self.ref = None

    @property
    def latt(self):
        """the lattice vector of the crystal cell"""
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

        Returns:
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

        Returns:
            list, shape (3,3)
        """
        if self._latt is None:
            latta, lattb, lattc = tuple(
                map(
                    lambda x: conv_estimate_number(self._blk.GetItemValue(x)),
                    ["_cell_length_a", "_cell_length_b", "_cell_length_c"],
                )
            )
            _logger.debug("cell length: %r , %r, %r", latta, lattb, lattc)
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

