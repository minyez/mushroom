# -*- coding: utf-8 -*-
"""FHI-aims related"""
import os
import re
from typing import Tuple, List, Dict, Union
from io import StringIO
from copy import deepcopy
import numpy as np

#from mushroom.core.cell import Cell
from mushroom.core.logger import create_logger
from mushroom.core.typehint import RealVec3D, Path
from mushroom.core.bs import BandStructure
from mushroom.core.ioutils import readlines_remove_comment, grep, open_textio
from mushroom.core.elements import element_symbols, get_atomic_number, l_channels

_logger = create_logger("aims")
del create_logger

def decode_band_output_line(bstr: str) -> Tuple[List, List, List]:
    """decode a line of band output file, e.g. scfband1001.out, band2001.out

    Each line is like

        index k1 k2 k3 occ_1 ene_1 occ_2 ene_2 ...

    Args:
        bstr (str)

    Returns:
        three list: k-points, occupation numbers, energies
    """
    values = bstr.split()
    try:
        kpts = list(map(float, values[1:4]))
        occ = list(map(float, values[4::2]))
        ene = list(map(float, values[5::2]))
        return kpts, occ, ene
    except IndexError as _e:
        raise ValueError(f"bad input string for aims band energy: {bstr}") from _e

def read_band_output(bfile, *bfiles, filter_k_before: int=0, filter_k_behind: int=None,
                     unit: str='ev') -> Tuple[BandStructure, List[RealVec3D]]:
    """read band output files and return a Band structure

    Note that all band energies are treated in the same spin channel,
    the resulting ``BandStructure`` object always has nspins=1

    Args:
        bfile (str)
        unit (str): unit of energies, default to ev

    Returns:
        BandStructure, k-points
    """
    bfiles = (bfile, *bfiles)
    kpts = []
    occ = []
    ene = []
    for bf in bfiles:
        _logger.info("Reading band output file: %s", bf)
        data = np.loadtxt(bf, unpack=True)
        kpts.extend(np.column_stack([data[1], data[2], data[3]]))
        occ.extend(np.transpose(data[4::2]))
        ene.extend(np.transpose(data[5::2]))
    kpts = np.array(kpts)
    if filter_k_behind is None:
        filter_k_behind = len(kpts)
    occ = np.array([occ,])[:, filter_k_before:filter_k_behind, :]
    ene = np.array([ene,])[:, filter_k_before:filter_k_behind, :]
    kpts = kpts[filter_k_before:filter_k_behind, :]
    return BandStructure(ene, occ, unit=unit), kpts

class Control:
    """object to handle aims control

    The arguments are all dictionaries.
    Keys are all strings.
    Value of general tags are also string.

    Args:
        tags (dict): general tags
        output (dict): tag controlling output
        species (dict)
    """

    def __init__(self, tags: Dict = None, output: Dict = None, species: List = None):
        self.tags = tags
        self.output = output
        self.species = species
        self._if_species_changed = False
        if self.species is not None:
            self._elements = [s.elem for s in self.species]

    def get_species(self, elem: Union[int, str]) -> int:
        """get the species object of element in the control"""
        if isinstance(elem, str):
            try:
                elem = self.elements.index(elem)
            except ValueError as _e:
                raise ValueError(f"species {elem} is not found in control") from _e
        return self.species[elem]

    # pylint: disable=W0707
    def get_tag(self, tag, *default):
        """get the value of tag"""
        try:
            return self.tags[tag]
        except KeyError:
            if default:
                return default[0]
            raise KeyError(f"no tag {tag} is found in control")

    # pylint: disable=W0707
    def get_output(self, tag, *default):
        """get the value of tag"""
        try:
            return self.output[tag]
        except KeyError:
            if default:
                return default[0]
            raise KeyError(f"no output tag {tag} is found in control")

    def update_tag(self, tag, value):
        """update the value of tag

        Args:
            tag (str): the tag to be updated
            value (str-able): the new value of the tag
                If set to None, the tag will be deleted
        """
        if value or value is False:
            try:
                v = {True: ".true.", False: ".false."}.get(value, str(value))
                self.tags[tag] = v
                _logger.info("tag '%s' updated to: %s", tag, v)
            except ValueError as _e:
                raise ValueError(f"cannot turn value into string: {value}") from _e
        else:
            try:
                _logger.info("removed tag '%s', original value: %s", tag, self.tags.pop(tag))
            except KeyError as _e:
                _logger.info("tag '%s' to remove is not defined, skip", tag)

    def update_output(self, output_tag, value):
        """update the output tag value

        Args:
            output_tag (str): the output tag to be updated
            value (str-able): the new value of the output tag
                set to False or None to delete the tag
        """
        if value:
            try:
                v = {True: ""}.get(value, str(value))
                self.output[output_tag] = v
                _logger.info("output tag '%s' updated to: %s", output_tag, v)
            except ValueError as _e:
                raise ValueError(f"cannot turn value into string: {value}") from _e
        else:
            try:
                _logger.info("removed output 'tag' %s, original value: %s", output_tag,
                             self.output.pop(output_tag))
            except KeyError as _e:
                _logger.info("output tag '%s' to remove is not defined, skip", output_tag)

    def get_basis(self, elem, *args, **kwargs):
        """get the basis of element ``elem``

        Args:
            elem (str or int): name of element, or its index in the control
            args and kwargs: parsed to the Species.get_basis method
        """
        s = self.get_species(elem)
        return s.get_basis(*args, **kwargs)

    def get_abf(self, elem, *args, **kwargs):
        """get the abf of element ``elem``

        Args:
            elem (str or int): name of element, or its index in the control
            args and kwargs: parsed to the Species.get_abf method
        """
        s = self.get_species(elem)
        return s.get_basis(*args, **kwargs)


    def add_basis(self, elem, *args, **kwargs):
        """add basis to speices of element ``elem``

        Args:
            elem (str or int): name of element, or its index in the control
            args and kwargs: parsed to the Species.add_basis method
        """
        s = self.get_species(elem)
        s.add_basis(*args, **kwargs)

    def add_abf(self, elem, *args, **kwargs):
        """add abf to speices of element ``elem``

        Args:
            elem (str or int): name of element, or its index in the control
            args and kwargs: parsed to the Species.add_abf method
        """
        s = self.get_species(elem)
        s.add_abf(*args, **kwargs)

    def modify_basis(self, elem, *args, **kwargs):
        """modify basis in speices of element ``elem``

        Args:
            elem (str or int): name of element, or its index in the control
            args and kwargs: parsed to the Species.modify_basis method
        """
        s = self.get_species(elem)
        s.modify_basis(*args, **kwargs)

    def modify_abf(self, elem, *args, **kwargs):
        """modify ABFs in speices of element ``elem``

        Args:
            elem (str or int): name of element, or its index in the control
            args and kwargs: parsed to the Species.modify_abf method
        """
        s = self.get_species(elem)
        s.modify_abf(*args, **kwargs)

    def delete_basis(self, elem, *args, **kwargs):
        """modify basis in speices of element ``elem``

        Args:
            elem (str or int): name of element, or its index in the control
            args and kwargs: parsed to the Species.delete_basis method
        """
        s = self.get_species(elem)
        s.delete_basis(*args, **kwargs)

    def delete_abf(self, elem, *args, **kwargs):
        """modify basis in speices of element ``elem``

        Args:
            elem (str or int): name of element, or its index in the control
            args and kwargs: parsed to the Species.delete_abf method
        """
        s = self.get_species(elem)
        s.delete_abf(*args, **kwargs)

    @property
    def elements(self):
        """the element name of the species"""
        if self._if_species_changed:
            self._elements = [s.elem for s in self.species]
            self._if_species_changed = False
        return self._elements

    def add_species(self, s, error_replace=False):
        """add species to the control file"""
        info = f"{s.elem} is already included in species"
        if s.elem in self.elements:
            if error_replace:
                raise ValueError(info)
            _logger.warning("%s, will replace", info)
            self.species[self.elements.index(s.elem)] = s
        else:
            self.species.append(s)
            self._if_species_changed = True

    def export(self):
        """export the control object to a string"""
        slist = ["# normal tags"]
        # normal tags
        slist.extend(f"{k} {v}" for k, v in self.tags.items())
        # output tags
        slist.append("# output tags")
        for k, v in self.output.items():
            if k != 'band':
                if v is True:
                    slist.append(f"output {k}")
                else:
                    slist.append(f"output {k} {v}")
            else:
                for kseg in v:
                    kstr = kseg[0] + kseg[1] + [kseg[2],]
                    # if the ksymbols are specied
                    if kseg[-1] is not None:
                        kstr.extend(kseg[-2:])
                    slist.append(f"output {k} {' '.join(str(x) for x in kstr)}")
        # species information
        slist.extend(s.export() for s in self.species)
        return "\n".join(slist)

    def write(self, pcontrol):
        """write the control content to file ``pcontrol``"""
        with open_textio(pcontrol, 'w') as h:
            print(self.export(), file=h)

    @classmethod
    def read(cls, pcontrol="control.in"):
        """Read aims control file and return an control object

        Note that global flags after species are excluded and all the comment are removed.
        """
        _logger.info("Reading control file: %s", pcontrol)
        _ls = readlines_remove_comment(pcontrol, keep_empty_lines=False, trim_leading_space=True)
        tags = {}
        # line number of each specie header
        species_ln = grep(r'species', _ls, return_linenum=True)
        if species_ln[1]:
            _logger.debug("Detected species: %r", [x.split()[1:] for x in species_ln[0]])
        else:
            _logger.warning("No species tag is found in control")

        # read all species information
        # delegate the reading to the Species object
        species_region = [*species_ln[1], len(_ls)]
        species = []
        for i, st in enumerate(species_region[:-1]):
            ed = species_region[i+1]
            species.append(Species.read(StringIO("\n".join(_ls[st:ed]))))

        # read other setup, including general tags and output tags
        i = 0
        output = []
        while i < len(_ls[:species_region[0]]):
            tagkv = _ls[i].split(maxsplit=1)
            tagk, tagv = tagkv[0], tagkv[1]
            if tagk == 'output':
                if tagv:
                    output.append(tagv)
                else:
                    _logger.warning("empty output tag, ignore")
            else:
                # single keyword without value
                # NOTE I am not sure if there is any single keyword without value in aims,
                #      though put here for safety
                if tagv:
                    tagv = tagkv[1]
                else:
                    tagv = ".true."
                tags[tagk] = tagv
            i += 1
        output = _read_output(output)
        _logger.debug("tags: %r", tags)
        _logger.debug("output: %r", output)
        _logger.debug("species: %r", species)
        return cls(tags, output, species)

def _read_output(lines):
    """read output tags in aims control file

    each element of lines is the text without output tag

    Note:
        For output tags like 'band', there can be multiple entries.
        Currently only 'band' of these tags are supported.
    """
    d = {}
    warn = "bad output tag line: %s"
    for l in lines:
        words = l.split()
        otag, ovalue = words[0], words[1:]
        if not ovalue:
            d[otag] = True
        elif len(ovalue) == 1:
            d[otag] = ovalue[0]
        else:
            if otag == 'band':
                d['band'] = d.get('band', [])
                if len(ovalue) in [7, 9]:
                    kpts = list(map(float, ovalue[:6]))
                    try:
                        kseg = [kpts[:3], kpts[3:], int(ovalue[6]), ovalue[7], ovalue[8]]
                    except IndexError:
                        kseg = [kpts[:3], kpts[3:], int(ovalue[6]), None, None]
                    d['band'].append(kseg)
                else:
                    _logger.warning(warn, l)
            else:
                d[otag] = ovalue
    return d


class Species:
    """object handling species

    Args:
        basis (dict): the basis set configuration.
            Each key should be in the ``basis_tag``.
            The value is a list, each element as a single string to specify the basis function.
        abf (dict): the same as basis, but used as auxiliary basis function (ABF)
    """
    species_basic_tag = ["nucleus", "mass", "l_hartree", "cut_pot", "basis_dep_cutoff",
                         "radial_base", "radial_multiplier", "angular_min", "angular_acc",
                         "innermost_max", "logarithmic", "include_min_basis", "pure_gauss",
                         "basis_acc", "cite_reference"]
    angular_grids_tag = ["angular_grids", "outer_grid", "division"]
    basis_tag = ["valence", "ion_occ", "hydro", "ionic", "gaussian", "sto"]

    def __init__(self, elem: str, tags: dict = None, basis: dict = None, abf: dict = None):
        self.elem = elem
        self.tags = tags
        self.basis = basis
        self.abf = abf

    @classmethod
    def _add_basis_common(cls, basis: dict, btype: str, bparam: str, *bparams):
        """add basis function to basis dictionary.

        The basis is defined by its type ``btype`` and a string with
        all required parameters ``bparam``.
        """
        if btype not in cls.basis_tag:
            raise ValueError(f"Invalid basis type: {btype}")
        if btype not in basis:
            basis[btype] = [bparam,]
        else:
            basis[btype].append(bparam)
        if bparams:
            basis[btype].extend(bparams)

    @classmethod
    def _get_basis_common(cls, basis: dict, btype: str = None):
        """get the basis function from the basis dictionary

        Args:
            btype (str)

        Returns:
            dict if btype is None, otherwise list
        """
        if btype is None:
            return deepcopy(basis)
        if btype not in cls.basis_tag:
            raise ValueError(f"Invalid basis type: {btype}")
        return basis.get(btype, None)

    def get_basis(self, btype: str = None):
        """get the basis of the species

        Args:
            btype (str)

        Returns:
            dict if btype is None, otherwise list
        """
        return self._get_basis_common(self.basis, btype)

    def get_abf(self, btype: str = None):
        """get the ABFs of the species

        Args:
            btype (str)

        Returns:
            dict if btype is None, otherwise list
        """
        return self._get_basis_common(self.abf, btype)

    def add_basis(self, btype: str, bparam: str, *bparams: str):
        """add basis function"""
        self._add_basis_common(self.basis, btype, bparam, *bparams)

    def add_abf(self, btype: str, bparam: str, *bparams: str):
        """add ABF"""
        self._add_basis_common(self.abf, btype, bparam, *bparams)

    @classmethod
    def _modify_basis_common(cls, basis: dict, btype: str, index: Union[int, str], bparam: str,
                             l_channel: str = None):
        """modify the basis function in basis dictionary

        Args:
            basis, btype and bparam: same to _add_basis_common.
                If bparam is set to None, the basis will be deleted.
            index: the index of the basis function to modify
            l_channel (str): name of l channel, i.e. s, p, d, f, etc.
                If not None, the index will counted within the particular l channel
        """
        if btype not in cls.basis_tag:
            raise ValueError(f"Invalid basis type: {btype}")
        if btype not in basis:
            raise ValueError(f"No {btype} type basis found in parsed basis dictionary")
        # the basis type list to be modified
        b = basis[btype]
        if l_channel is None:
            indices = list(range(len(b)))
        else:
            # l at column 2: hydro, valence, ion_occ, ionic
            if btype in ["hydro", "valence", "ion_occ", "ionic"]:
                indices = [i for i, v in enumerate(b) if v.split()[1] == l_channel]
            # l at column 1: gaussian in angular momentum
            elif btype in ["gaussian",]:
                indices = [i for i, v in enumerate(b)
                           if l_channels[int(v.split()[0])] == l_channel]
            else:
                raise NotImplementedError
        if isinstance(index, str):
            try:
                index = int(index)
            except ValueError as _e:
                raise ValueError(f"invalid index: {index}") from _e
        try:
            index = indices[index]
        except IndexError as _e:
            info = f"basis of index {index} is not available"
            if l_channel is not None:
                info = f"basis of index {index} in {l_channel} is not available"
            raise IndexError(info) from _e
        if bparam is None:
            del b[index]
        else:
            b[index] = bparam

    def modify_basis(self, btype: str, index: Union[int, str], bparam: str, l_channel: str = None):
        """modify basis function"""
        self._modify_basis_common(self.basis, btype, index, bparam, l_channel)

    def delete_basis(self, btype: str, index: Union[int, str], l_channel: str = None):
        """delete basis function"""
        self._modify_basis_common(self.basis, btype, index, None, l_channel)

    def modify_abf(self, btype: str, index: Union[int, str], bparam: str, l_channel: str = None):
        """modify ABF"""
        self._modify_basis_common(self.abf, btype, index, bparam, l_channel)

    def delete_abf(self, btype: str, index: Union[int, str], l_channel: str = None):
        """delete ABF"""
        self._modify_basis_common(self.abf, btype, index, None, l_channel)

    @classmethod
    def _export_basis_common(cls, basis: dict, prefix: str):
        """export the basis set configuration

        The order follows the ``basis_tag`` class attribute

        Args:
            basis (dict)
            prefix (str): added just before the tag of ``basis_tag``
        """
        slist = []
        for bt in cls.basis_tag:
            if bt not in basis:
                continue
            if bt != 'gaussian':
                for b in basis[bt]:
                    slist.append(f"{prefix}{bt} {b}")
            else:
                for b in basis[bt]:
                    n = b.split()[1]
                    # pGTO
                    if int(n) == 1:
                        slist.append(f"{prefix}{bt} {b}")
                    # cGTO
                    else:
                        cgto = b.split()
                        slist.append(f"{prefix}{bt} {cgto[0]} {cgto[1]}")
                        for i in range(int(n)):
                            slist.append(f"{cgto[2*i+2]:>17s}  {cgto[2*i+3]:>13s}")
        return "\n".join(slist)

    def _export_basis(self):
        """export the basis to a string"""
        return self._export_basis_common(self.basis, '')

    def _export_abf(self):
        """export the ABFs to a string"""
        return self._export_basis_common(self.abf, 'for_aux ')

    def export(self):
        """export the species to a string"""
        slist = ["### Start species ###",
                 f"species  {self.elem}"]
        for t in self.tags:
            if t in self.species_basic_tag:
                slist.append(f"  {t}  {self.tags[t]}")
            if t == 'angular_grids':
                slist.append(f"  {t}  {self.tags[t]['method']}")
                for div in self.tags[t]['division']:
                    slist.append(f"    division  {div}")
                slist.append(f"    outer_grid  {self.tags[t]['outer_grid']}")
        slist.append(self._export_basis())
        slist.append(self._export_abf())
        slist.append("###   End species ###")
        return "\n".join(slist)

    def write(self, pspecies):
        """write the species content to file ``pspecies``"""
        with open(pspecies, 'w', encoding='utf-8') as h:
            print(self.export(), file=h)

    # pylint: disable=R0912,R0914,R0915
    @classmethod
    def read(cls, pspecies):
        """read in the species from a filelike object"""
        _ls = readlines_remove_comment(pspecies, keep_empty_lines=False, trim_leading_space=True)
        try:
            elem = _ls[0].split()[1]
            assert elem in element_symbols[1:]
        except IndexError as _e:
            raise ValueError(f"Invalid species head {_ls[0]}") from _e
        except AssertionError as _e:
            raise ValueError(f"Unknown species: {elem}") from _e
        _logger.info("handling species: %s", elem)
        tags = {}
        basis = {}
        abf = {}
        agt = cls.angular_grids_tag[0]
        i = 0
        while i < len(_ls):
            if _ls[i].strip().startswith('#'):
                i += 1
                continue
            tagk, tagv = _ls[i].strip().split(maxsplit=1)
            # handle general species tags
            if tagk in cls.species_basic_tag:
                tags[tagk] = tagv
            if tagk in cls.angular_grids_tag:
                if agt not in tags:
                    tags[agt] = {'method': None, 'division': []}
                if tagk == agt:
                    tags[agt]['method'] = tagv
                elif tagk == 'division':
                    tags[agt]['division'].append(tagv)
                else:
                    tags[agt][tagk] = tagv
            # handle basis set configuration
            basis_dict = basis
            basis_key = 'basis'
            if tagk == 'for_aux':
                basis_dict = abf
                basis_key = 'abf'
                tagk, tagv = tagv.strip().split(maxsplit=1)
            if tagk in cls.basis_tag:
                if tagk not in basis_dict:
                    basis_dict[tagk] = []
                vals = tagv.split()
                if tagk == 'gaussian':
                    # pGTO
                    if int(vals[1]) == 1:
                        basis_dict[tagk].append(tagv)
                        _logger.debug("append pGTO %s: %s", basis_key, tagv)
                    # cGTO
                    else:
                        # head plus the following vals[1] _ls
                        cgtos = [tagv,]
                        for x in _ls[i+1:i+1+int(vals[1])]:
                            cgtos.extend(x.split())
                        basis_dict[tagk].append(" ".join(cgtos))
                        i += int(vals[1])
                        _logger.debug("append cGTO %s: %s", basis_key, " ".join(cgtos))
                else:
                    basis_dict[tagk].append(tagv)
                    _logger.debug("append %s %s: %s", tagk, basis_key, tagv)
            i += 1
        return cls(elem, tags, basis, abf)

    @classmethod
    def read_default(cls, elem: str, level: str = "intermediate",
                     category: str = "defaults_2020"):
        """load the default setting in 'species_defaults' directory

        It is actually a convenient function to use the ``read`` method.
        It extracts the ``AIMS_SPECIES_DEFAULTS`` environment variable,
        load the available categories

        Args:
            elem (str): element of the species
            level (str): 'light', 'intermediate', etc for defaults, and n for NAO-J/NAO-VCC basis
                For non-standard basis, you have to specify the level below "non-standard",
                e.g. "cc-pVDZ" and set category to "non-standard"
            category (str): the category.
                It is the directory name under species_defaults for standard basis,
                and the name under non-standard for non-standard basis.
        """
        # non-standard basis
        species_defaults_ev = "AIMS_SPECIES_DEFAULTS"
        try:
            species_defaults = os.environ[species_defaults_ev]
        except KeyError as _e:
            raise KeyError(f"Environment variable {species_defaults_ev} is not set") from _e
        pspecies = []
        if level not in ["intermediate", "light", "light_spd", "really_tight", "tight"]:
            _logger.info("Querying non-standard basis")
            pspecies.append("non-standard")
        elem_id = get_atomic_number(elem)
        pspecies.extend([category, level, f"{elem_id}_{elem}_default"])
        pspecies = os.path.join(species_defaults, *pspecies)
        return cls.read(pspecies)

class StdOut:
    """a general-purpose object to handle aims standard output

    Currently only support handling SCF and post-SCF.

    Args:
        pstdout (Path): path to the aims standard output file
    """

    def __init__(self, pstdout: Path):
        with open(pstdout, 'r', encoding='utf-8') as h:
            lines = h.readlines()
        _logger.info("Reading standard output from: %s", pstdout)
        self._finished = lines[-2].strip() == 'Have a nice day.'
        _logger.info("  Finished? %s", self._finished)
        self._finished_prep = False
        self._finished_init  = False
        self._prep_lines = None
        self._init_lines = None
        self._scf_lines = None
        self._postscf_lines = None
        self._nspins = None
        for i, l in enumerate(lines):
            if l.startswith("  Preparations completed."):
                self._finished_prep = True
                self._prep_lines = lines[:i]
            if l.startswith("          Begin self-consistency loop: Initialization."):
                self._finished_init = True
                self._init_lines = lines[i:]
            if l.startswith("          Begin self-consistency iteration #    1"):
                self._init_lines = self._init_lines[:self._init_lines.index(l)]
                self._scf_lines = lines[i:]
            # use the start of constructing auxillary basis as a mark for post-scf calculations
            if l.startswith("  Constructing auxiliary basis"):
                self._scf_lines = self._scf_lines[:self._scf_lines.index(l)]
                self._postscf_lines = lines[i:]

        self._nkpts = None
        self._nbasis_H = None
        self._nelect = None
        self._nbasis_uc = None
        self._control = None
        self._geometry = None

        self._handle_prep()
        self._handle_init()

    def _handle_prep(self):
        """process the information in the header part, i.e. data before the self-consistency loop"""
        # the control information
        if not self._finished_prep:
            _logger.warning("preparation is not finished")
        for i, l in enumerate(self._prep_lines):
            if l.startswith("| Number of spin channels           :"):
                self._nspins = int(l.split()[-1])

    def _handle_init(self):
        """process the data in the self-consistency loop initialization"""
        if not self._finished_init:
            _logger.warning("self-consistent loop initialization is not finished")
        for i, l in enumerate(self._init_lines):
            if l.startswith("  Initializing the k-point"):
                try:
                    self._nkpts = int(self._init_lines[i+1].split()[-1])
                except (IndexError, ValueError):
                    pass
            if l.startswith("  | Number of basis functions in the Hamiltonian integrals"):
                self._nbasis_H = int(l.split()[-1])
            if l.startswith("  | Number of basis functions in a single unit cell"):
                self._nbasis_uc = int(l.split()[-1])
            if l.startswith("  | Initial density: Formal number of electrons"):
                self._nelect = float(l.split()[-1])

    @property
    def nelect(self):
        """the integer number of electrons"""
        return int(np.rint(self._nelect))

    def _handle_scf(self):
        """process the data in the self-consistency iterations"""

    def get_control(self):
        """return a Control object"""
        raise NotImplementedError

    def get_geometry(self):
        """return a Cell object representing the geometry"""
        raise NotImplementedError

    def get_QP_result(self):
        """get the aims QP result from the standard output

        The dict includes 6 items, with their key corresponding to each data column
        in the output file:
        - ``occ`` : occupation number (occ_num),
        - ``eps`` : starting-point eigenvalues (e_gs)
        - ``exx`` : exact exchange contribution (e_x^ex),
        - ``vxc`` : xc contribution to starting-point (e_xc^gs)
        - ``sigc``: non-local correlation from self-energy (e_c^nloc)
        - ``eqp`` : QP energy (e_qp).

        Note the names of keys differ from the column names, since they are adapted
        according to their meaning so that the keys are consistent across different
        programs. The value is a (nspins, nkpoints, nbands) array.

        Returns:
            a dict
        """
        errmsg = "Post-SCF calculations is not {} from the standard output"
        if self._postscf_lines is None:
            raise TypeError(errmsg.format('recognized'))
        st = None
        ed = None
        # looking for the header of the GW result part
        for i, l in enumerate(self._postscf_lines):
            if l.strip().startswith("GW quasi-particle energy levels"):
                st = i
            if l.strip().startswith("DFT/Hartree-Fock") \
                    or l.strip().startswith("Valence band maximum (VBM) from the GW") \
                    or l.strip().startswith("Spin-up valence band maximum"):
                ed = i
        if st is None or ed is None:
            raise ValueError(errmsg.format('finished'))
        eqpline = re.compile(r'^\s*(\d+)' + r'\s+(-?[\d\.]+)'*6 + r'(\\n)?$')
        # search the data
        array = []
        istates = []
        for l in self._postscf_lines[st:ed]:
            m = eqpline.match(l)
            if m:
                istates.append(int(m.group(1)))
                array.append([*map(float, (m.group(i) for i in range(2, 8)))])
        array = np.array(array)
        # reshape all arrays. Generally, the first state is a fully occupied core state
        # thus the number of spins can be decided from its occupation number
        # this is usually not used, as the channel should be printed at the preparation stage
        if self._nspins is None:
            nspins = 1
            if array[0, 0] == 1:
                nspins = 2
            self._nspins = nspins
        # the number of kpoints to print, not necessary that used in SCF
        nkpts = istates.count(istates[0]) // self._nspins
        #nbands = istates[1:].index(istates[0]) + 1
        # TODO: verify that kmesh goes faster than spin
        #       otherwise one may swap the first two axis
        keys = ["occ", "eps", "exx", "vxc", "sigc", "eqp"]
        d = {}
        for i, k in enumerate(keys):
            d[k] = array[:, i].reshape(self._nspins, nkpts, -1, order="C")
        return d

    def get_QP_bandstructure(self, kind="eqp"):
        """get the QP band structure

        Args:
            kind (str): the key of QP energies, default to "eqp".
                using "eps" can be viewed as a helper function to get the KS band structure

        Returns
            BandStructure object
        """
        d = self.get_QP_result()
        if kind not in ["eqp", "eps"]:
            raise ValueError("Use eqp/eps for QP/KS band structure")
        # TODO: which case does the occupation number refer to when
        #       there is a band reordering?
        return BandStructure(d[kind], d["occ"], unit='ev')

