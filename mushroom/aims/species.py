# -*- coding: utf-8 -*-
"""Class to handle basis set for atom species"""
import os
import pathlib
from typing import Union
from io import StringIO
from copy import deepcopy

from mushroom.core.elements import element_symbols, get_atomic_number, l_channels
from mushroom.core.ioutils import open_textio
from mushroom.core.logger import loggers


_logger = loggers["aims"]

_SPECIES_DEFAULTS_ENV = "AIMS_SPECIES_DEFAULTS"


def search_basis_directories(aims_species_defaults=None, error_dir_not_found: bool = True):
    if aims_species_defaults is None:
        aims_species_defaults = get_species_defaults_directory()
    if error_dir_not_found and not os.path.isdir(aims_species_defaults):
        raise ValueError("specified aims_species_defaults {} is not a directory"
                         .format(aims_species_defaults))
    root_dir = pathlib.Path(aims_species_defaults)
    paths = []
    for path in root_dir.glob('**/01_H_default'):
        spath = str(path)
        paths.append(os.path.dirname(spath[len(os.path.commonprefix([path, root_dir])) + 1:]))

    return paths


def get_basis_directory_from_alias(directory_alias):
    """get the directory name from alias"""
    directory = directory_alias.lower()
    if directory in ['light', 'intermediate', 'tight', 'really_tight']:
        directory = os.path.join("defaults_2020", directory)
    elif directory in ['cc-pvdz', 'cc-pvtz', 'cc-pvqz',
                       'aug-cc-pvdz', 'aug-cc-pvtz', 'aug-cc-pvqz']:
        directory = os.path.join("non-standard", "gaussian_tight_770",
                                 directory[:directory.index('v')] + directory[-3:].upper())
    elif directory in ["nao-j-2", "nao-j-3", "nao-j-4", "nao-j-5"]:
        directory = os.path.join("NAO-J-n", directory.upper())
    elif directory in ["nao-vcc-2z", "nao-vcc-3z", "nao-vcc-4z", "nao-vcc-5z"]:
        directory = os.path.join("NAO-VCC-nZ", directory.upper())
    return directory


def get_species_defaults_directory():
    """get the directory of species_defaults from environment variable and configuration"""
    try:
        species_defaults = os.environ[_SPECIES_DEFAULTS_ENV]
    except KeyError as _e:
        try:
            from mushroom.__config__ import aims_species_defaults as species_defaults
        except ImportError:
            raise KeyError("Environment variable {} or aims_species_defaults in config file is required"
                           .format(_SPECIES_DEFAULTS_ENV))
    if not os.path.isdir(species_defaults):
        raise ValueError("species_defaults {} is not a directory".format(species_defaults))
    return species_defaults


def get_specie_filename(elem: str,
                        directory: str,
                        species_defaults: str = None,
                        error_dir_not_found: bool = True):
    """get the name of specie file of a particular basis

    Args:
        elem (str)
        directory (str): directory of species category or its alias
        species_defaults (str)

    Returns:
        str
    """
    elem_id = get_atomic_number(elem, False)
    if species_defaults is None:
        species_defaults = get_species_defaults_directory()
    directories_avail = search_basis_directories(species_defaults, error_dir_not_found=error_dir_not_found)
    directory = directory.strip("/")
    directory = get_basis_directory_from_alias(directory)
    if error_dir_not_found and directory not in directories_avail:
        raise ValueError("{} is not found in available basis directories {}"
                         .format(directory, directories_avail))
    pspecies = [species_defaults, directory, f"{elem_id:02d}_{elem}_default"]
    pspecies = os.path.join(*pspecies)
    return pspecies


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
                         "basis_acc", "cite_reference",
                         "plus_u"]
    # TODO: accept multiple plus_u, so we need a list to store it
    angular_grids_tag = ["angular_grids", "outer_grid", "division"]
    basis_tag = ["valence", "ion_occ", "hydro", "ionic", "gaussian", "sto"]

    def __init__(self, elem: str, tags: dict = None, basis: dict = None, abf: dict = None,
                 header: str = None):
        self.elem = elem
        self.tags = tags
        self.basis = basis
        self.abf = abf
        self.header = header

    def update_basic_tag(self, tag, value):
        """update the value of basic species tag

        Args:
            tag (str): the basic tag to be updated
            value (str-able): the new value of the tag
                If set to None or empty list, the tag will be deleted
        """
        if tag not in self.species_basic_tag:
            raise KeyError(f"not a supported species tag: {tag}")
        if value or value is False:
            try:
                v = {True: ".true.", False: ".false."}.get(value, str(value))
                self.tags[tag] = v
                _logger.info("tag '%s' updated to: %s", tag, v)
            except ValueError:
                raise ValueError(f"cannot turn value into string: {value}")
        else:
            try:
                _logger.info("removed tag '%s', original value: %s", tag, self.tags.pop(tag))
            except KeyError:
                _logger.info("tag '%s' to remove is not defined, skip", tag)

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
    def _export_basis_common(cls, basis: dict, prefix: str, padding: int = 0):
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
                    slist.append(" " * padding + f"{prefix}{bt} {b}")
            else:
                for b in basis[bt]:
                    n = b.split()[1]
                    # pGTO
                    if int(n) == 1:
                        slist.append(" " * padding + f"{prefix}{bt} {b}")
                    # cGTO
                    else:
                        cgto = b.split()
                        slist.append(" " * padding + f"{prefix}{bt} {cgto[0]} {cgto[1]}")
                        for i in range(int(n)):
                            slist.append(" " * padding + f"{cgto[2*i+2]:>17s}  {cgto[2*i+3]:>13s}")
        return "\n".join(slist)

    def _export_basis(self, padding: int = 0):
        """export the basis to a string"""
        return self._export_basis_common(self.basis, '', padding)

    def _export_abf(self, padding: int = 0):
        """export the ABFs to a string"""
        return self._export_basis_common(self.abf, 'for_aux ', padding)

    def export(self, padding: int = 0):
        """export the species to a string"""
        header = "### Start species ###"
        if self.header is not None:
            header = self.header
        slist = [header,
                 " " * padding + f"species  {self.elem}"]
        padding = padding + 2
        for t in self.tags:
            if t in self.species_basic_tag:
                slist.append(" " * padding + f"{t}  {self.tags[t]}")
            if t == 'angular_grids':
                slist.append(" " * padding + f"{t}  {self.tags[t]['method']}")
                for div in self.tags[t]['division']:
                    slist.append(" " * padding + f"  division  {div}")
                slist.append(" " * padding + f"  outer_grid  {self.tags[t]['outer_grid']}")
        if self.basis is not None and self.basis.keys():
            slist.append(self._export_basis(padding))
        if self.abf is not None and self.abf.keys():
            slist.append(self._export_abf(padding))
        if self.header is None:
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
        with open_textio(pspecies, 'r') as h:
            _ls = h.readlines()
        elem = None
        tags = {}
        basis = {}
        abf = {}
        agt = cls.angular_grids_tag[0]
        i = 0
        headerl = []
        while i < len(_ls):
            l = _ls[i].strip()
            # print(l, elem, l.startswith("species"))
            if elem is None and not l.startswith("species"):
                headerl.append(l)
            if l.startswith('#') or l == '':
                i += 1
                continue
            tagk, tagv = _ls[i].strip().split(maxsplit=1)
            # handle general species tags
            if tagk == "species":
                # skip the element identifier
                elem = tagv
            elif tagk in cls.species_basic_tag:
                tags[tagk] = tagv
            elif tagk in cls.angular_grids_tag:
                if agt not in tags:
                    tags[agt] = {'method': None, 'division': []}
                if tagk == agt:
                    tags[agt]['method'] = tagv
                elif tagk == 'division':
                    tags[agt]['division'].append(tagv)
                else:
                    tags[agt][tagk] = tagv
            # handle basis set configuration
            elif tagk == "for_aux" or tagk in cls.basis_tag:
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
                            for x in _ls[i + 1:i + 1 + int(vals[1])]:
                                cgtos.extend(x.split())
                            basis_dict[tagk].append(" ".join(cgtos))
                            i += int(vals[1])
                            _logger.debug("append cGTO %s: %s", basis_key, " ".join(cgtos))
                    else:
                        basis_dict[tagk].append(tagv)
                        _logger.debug("append %s %s: %s", tagk, basis_key, tagv)
            else:
                info = "Unknown species tag {} on line {}, break for safety".format(tagk, i + 1)
                _logger.error(info)
                raise ValueError(info)
            i += 1
        if elem not in element_symbols[1:]:
            raise ValueError(f"Unknown element: {elem}")
        _logger.info("handling species of element: %s", elem)
        header = None
        if len(headerl) > 0:
            header = "\n".join(headerl)
        return cls(elem, tags, basis, abf, header=header)

    @classmethod
    def read_multiple(cls, pspecies):
        """similar to read, but intended for a file containing multiple species,

        Returns:
            list of Species object
        """
        with open(pspecies, 'r') as h:
            lines = h.readlines()
        elemline_indices = []
        species = []
        for i, l in enumerate(lines):
            if l.strip().startswith("species"):
                elemline_indices.append(i)
        for i, ielem in enumerate(elemline_indices):
            if i == len(elemline_indices) - 1:
                species.append(cls.read(StringIO("".join(lines[ielem:]))))
            else:
                species.append(
                    cls.read(
                        StringIO("".join(lines[ielem:elemline_indices[i + 1]]))))
        return species

    @classmethod
    def read_default(cls, elem: str, directory: str = "defaults_2020/intermediate"):
        """load the default setting in 'species_defaults' directory

        It is actually a convenient function to use the ``read`` method.
        It extracts the ``AIMS_SPECIES_DEFAULTS`` environment variable,
        If it is not available, it will read ``aims_species_defaults`` variable
        in the configuration file.

        Args:
            elem (str): element of the species
            directory (str): the directory where the species files lie, e.g.
                'defaults_2020/light', 'defaults_2020/intermediate', 'NAO-VCC' basis
                For non-standard basis, you have to specify the level below "non-standard",
                e.g. "cc-pVDZ" and set category to "non-standard"
        """
        species_defaults = get_species_defaults_directory()
        pspecies = get_specie_filename(elem, directory, species_defaults)
        return cls.read(pspecies)
