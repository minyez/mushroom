# -*- coding: utf-8 -*-
"""Class to handle basis set for atom species"""
import os
import pathlib
from typing import Union
from io import StringIO
from copy import deepcopy

from mushroom.core.elements import element_symbols, get_atomic_number, l_channels, l_int
from mushroom.core.ioutils import open_textio
from mushroom.core.logger import loggers


__all__ = [
    "Species",
    "readlines_species_defaults",
]
_logger = loggers["aims"]

_SPECIES_DEFAULTS_ENV = "AIMS_SPECIES_DEFAULTS"

BASIS_KEYS = ["valence", "ion_occ", "hydro", "ionic", "gaussian", "sto", "confined"]


def get_num_obfs(basis_key, basis_string):
    """Get the number of orbital basis functions of ``basis_key`` basis represented by ``basis_string``

    Args:
        basis_key (str)
        basis_string (str)

    Return:
        int
    """
    if basis_key in ["valence", "ion_occ"]:
        n, lstr, _ = basis_string.split()
        l = l_int[lstr]
        return (2 * l + 1) * (int(n) - l)
    elif basis_key in ["hydro", "ionic", "confined"]:
        n, lstr, _ = basis_string.split()
        return 2 * l_int[lstr] + 1
    elif basis_key == "sto":
        n, l, _ = basis_string.split()
        return 2 * int(l) + 1
    elif basis_key == "gaussian":
        l, n_pgto = basis_string.split()[:2]
        return (2 * int(l) + 1) * int(n_pgto)
    raise ValueError("Unknown basis type with key: {}".format(basis_key))


def get_l_nrad(basis_key, basis_string):
    """Get angular momentum number and number of radial functions of ``basis_key`` basis represented by ``basis_string``

    Args:
        basis_key (str)
        basis_string (str)

    Return:
        int
    """
    if basis_key in ["valence", "ion_occ"]:
        n, lstr, _ = basis_string.split()
        l = l_int[lstr]
        return l, int(n) - l
    elif basis_key in ["hydro", "ionic", "confined"]:
        _, lstr, _ = basis_string.split()
        return l_int[lstr], 1
    elif basis_key == "sto":
        _, l, _ = basis_string.split()
        return int(l), 1
    elif basis_key == "gaussian":
        l, n_pgto = basis_string.split()[:2]
        return int(l), int(n_pgto)
    raise ValueError("Unknown basis type with key: {}".format(basis_key))


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
    _logger.debug("Avail defaults: %r", paths)

    return paths


def get_basis_directory_from_alias(directory_alias):
    """get the directory name from alias"""
    directory = directory_alias.lower()
    if directory in ['light', 'intermediate', 'tight', 'really_tight',
                     'intermediate_gw', 'tight_gw', 'really_tight_gw']:
        directory = os.path.join("defaults_2020", directory)
    elif directory in ['cc-pvdz', 'cc-pvtz', 'cc-pvqz',
                       'aug-cc-pvdz', 'aug-cc-pvtz', 'aug-cc-pvqz']:
        directory = os.path.join("non-standard", "gaussian_tight_770",
                                 directory[:directory.index('v')] + directory[-3:].upper())
    elif directory in ["nao-j-2", "nao-j-3", "nao-j-4", "nao-j-5"]:
        directory = os.path.join("NAO-J-n", directory.upper())
    elif directory in ["nao-vcc-2z", "nao-vcc-3z", "nao-vcc-4z", "nao-vcc-5z"]:
        directory = os.path.join("NAO-VCC-nZ", directory.upper())
    else:
        raise ValueError("Unknown alias for basis directory: {}".format(directory_alias))
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


def get_species_filepaths(directory: str,
                          elem: str, *elems: str,
                          species_defaults: str = None,
                          error_dir_not_found: bool = True):
    """get the paths of species files of a particular basis

    Args:
        directory (str): directory of species category or its alias
        elem and elems (str)
        species_defaults (str)

    Returns:
        List of str
    """
    if species_defaults is None:
        species_defaults = get_species_defaults_directory()
    directories_avail = search_basis_directories(species_defaults, error_dir_not_found=error_dir_not_found)
    directory = directory.strip("/")
    print("H")
    _logger.debug("Checking for %s", directory)
    # possibly an alias
    if "/" not in directory:
        _logger.debug("Checking alias for %s", directory)
        directory = get_basis_directory_from_alias(directory)
    if error_dir_not_found and directory not in directories_avail:
        raise ValueError("{} is not found in available basis directories {}"
                         .format(directory, directories_avail))
    elems = [elem, *elems]
    pspecies = []
    for e in elems:
        elem_id = get_atomic_number(e, False)
        pspecies.append(os.path.join(*[species_defaults, directory, f"{elem_id:02d}_{e}_default"]))
    return pspecies


def readlines_species_defaults(directory: str, elem: str, *elems: str, species_defaults: str = None):
    """read the species files specified by `directory` and elements `elem` and `elems`

    Args:
        directory (str): directory of species category or its alias
        elem and elems (str)
        species_defaults (str)
    """
    lines = []
    for pspecie in get_species_filepaths(directory, elem, *elems,
                                         species_defaults=species_defaults, error_dir_not_found=True):
        with open(pspecie, 'r') as h:
            lines.extend(h.readlines())
    return "".join(lines)


class NaoBasisPool:
    """"""


class Species:
    """object handling species

    Args:
        basis (list): the basis set configuration.
            The value is a list, each element representes a basis function.
            Each member should be a list ``[basis_type, basis_string, is_aux, tier, enabled]``,
            where
            - ``basis_type`` should be one of the basis type in ``Species.basis_types``.
            - ``basis_string`` is string representing the left information to define the basis
            - ``is_aux`` should be a bool, whether this basis is only used for constructing
              auxliary basis
            - ``tier`` should be a non-negative integer or None.
              0 stands for minimal basis, 1 for tier1 and so on so forth.
            - ``enabled`` is a bool. When True, the basis will be exported but commented out.
    """
    species_basic_tag = ["nucleus", "mass", "l_hartree", "cut_pot", "basis_dep_cutoff",
                         "radial_base", "radial_multiplier", "angular_min", "angular_acc",
                         "innermost_max", "logarithmic", "include_min_basis", "pure_gauss",
                         "basis_acc", "cite_reference",
                         "plus_u"]
    # TODO: accept multiple plus_u, so we need a list to store it
    angular_grids_tag = ["angular_grids", "outer_grid", "division"]
    basis_types = BASIS_KEYS
    # TODO: use regular expression pattern to match the basis function lines
    # TODO: move basis set reading to NaoBasis class

    def __init__(self, elem: str, tags: dict = None, basis: list = None,
                 header: str = None):
        self.elem = elem
        self.tags = tags
        self.basis = basis
        self.header = header

    @classmethod
    def _check_basis_type(cls, basis_type: str):
        if basis_type not in cls.basis_types:
            raise ValueError(f"Unsupported basis type: {basis_type}")

    def __getitem__(self, tag):
        return self.tags[tag]

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

    def add_basis(self, basis_type: str, basis_string: str, *basis_strings: str,
                  is_aux: bool = False, tier: int = -1, enabled: bool = True):
        """Add basis function to the species

        Args:
            basis_type (str)
            basis_string (str)
            basis_strings (str)
            is_aux (bool): whether this function is used only to construct ABF
            tier (int): if the basis belongs to some tier.
                0 for minimal and < 0 for not belong to any tier
            enabled (bool): if the basis is enabled when exporting.
                If False, the basis is commented out when exporting
        """
        self._check_basis_type(basis_type)
        basis_string = " ".join(basis_string.split())
        new_basis = [basis_type, basis_string, is_aux, tier, enabled]
        self.basis.append(new_basis)
        _logger.debug("add basis '%s'", new_basis)
        if basis_strings is not None:
            for bs in basis_strings:
                new_basis = [basis_type, " ".join(bs.split()), is_aux, tier, enabled]
                _logger.debug("add basis '%s'", new_basis)
                self.basis.append(new_basis)

    def add_abf(self, basis_type: str, basis_string: str, *basis_strings: str,
                tier: int = -1, enabled: bool = True):
        """A wrapper of add_basis method for auxliary basis functions"""
        self.add_basis(basis_type, basis_string, *basis_strings, is_aux=True, tier=tier, enabled=enabled)

    def get_basis(self,
                  basis_type: str = None,
                  is_aux: bool = None,
                  tier: int = None,
                  enabled: bool = None):
        """get the basis functions

        Args:
            basis_type (str)
            is_aux (bool)
            tier (int)

        Returns:
            list
        """
        if basis_type is not None:
            self._check_basis_type(basis_type)
        basis = []
        if basis_type is None and is_aux is None and tier is None and enabled is None:
            return deepcopy(self.basis)

        for b in self.basis:
            if basis_type is not None and b[0] != basis_type:
                continue
            if is_aux is not None and b[2] != is_aux:
                continue
            if tier is not None and b[3] != tier:
                continue
            if enabled is not None and b[4] != enabled:
                continue
            basis.append(b)
        return basis

    def get_abf(self,
                basis_type: str = None,
                tier: int = None):
        """A wrapper of get_basis method for auxliary basis functions"""
        return self.get_basis(basis_type=basis_type, is_aux=True, tier=tier)

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
        raise NotImplementedError
        # if btype not in cls.basis_types:
        #     raise ValueError(f"Invalid basis type: {btype}")
        # if btype not in basis:
        #     raise ValueError(f"No {btype} type basis found in parsed basis dictionary")
        # # the basis type list to be modified
        # b = basis[btype]
        # if l_channel is None:
        #     indices = list(range(len(b)))
        # else:
        #     # l at column 2: hydro, valence, ion_occ, ionic
        #     if btype in ["hydro", "valence", "ion_occ", "ionic"]:
        #         indices = [i for i, v in enumerate(b) if v.split()[1] == l_channel]
        #     # l at column 1: gaussian in angular momentum
        #     elif btype in ["gaussian",]:
        #         indices = [i for i, v in enumerate(b)
        #                    if l_channels[int(v.split()[0])] == l_channel]
        #     else:
        #         raise NotImplementedError
        # if isinstance(index, str):
        #     try:
        #         index = int(index)
        #     except ValueError as _e:
        #         raise ValueError(f"invalid index: {index}") from _e
        # try:
        #     index = indices[index]
        # except IndexError as _e:
        #     info = f"basis of index {index} is not available"
        #     if l_channel is not None:
        #         info = f"basis of index {index} in {l_channel} is not available"
        #     raise IndexError(info) from _e
        # if bparam is None:
        #     del b[index]
        # else:
        #     b[index] = bparam

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

    def switch_tier(self, tier: int, enable: bool, switch_aux: bool = True):
        """Switch the status of functions within a tier"""
        for b in self.basis:
            if b[3] == tier:
                if not switch_aux and b[2]:
                    continue
                b[4] = enable

    def export_basis(self, padding: int = 0):
        """export the basis set configuration

        The order follows the ``basis_tag`` class attribute

        Args:
            basis_key (str)
            prefix (str): added just before the tag of ``basis_tag``
        """
        slist = []
        tier_string_dict = {
            0: "Minimal basis",
            1: "First Tier",
            2: "Second Tier",
            3: "Third Tier",
            4: "Fourth Tier",
            5: "Fifth Tier",
            -1: "Further basis functions"
        }
        tier_export_list = [0, 1, 2, 3, 4, 5, -1]

        for tier_export in tier_export_list:
            slist_tier = []
            for btype, bstr, is_aux, tier, enabled in self.basis:
                comment = {True: "", False: "# "}[enabled]
                for_aux = {True: "for_aux ", False: ""}[is_aux]
                if tier != tier_export:
                    continue
                _logger.debug("Exporting basis %s %s %r %s %r", btype, bstr, is_aux, tier, enabled)
                if btype != 'gaussian':
                    slist_tier.append(comment + " " * padding + f"{for_aux}{btype} {bstr}")
                else:
                    n = bstr.split()[1]
                    # pGTO
                    if int(n) == 1:
                        slist_tier.append(comment + " " * padding + f"{for_aux}{btype} {bstr}")
                    # cGTO
                    else:
                        cgto = bstr.split()
                        slist_tier.append(comment + " " * padding + f"{for_aux}{btype} {cgto[0]} {cgto[1]}")
                        for i in range(int(n)):
                            slist_tier.append(comment + " " * padding + f"{cgto[2*i+2]:>17s}  {cgto[2*i+3]:>13s}")
            # only export existing tiers
            if len(slist_tier) > 0:
                slist.append("#  " + tier_string_dict[tier_export])
                slist.extend(slist_tier)
        return "\n".join(slist)

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
        slist.append(self.export_basis(padding))
        # if self.header is not None:
        #     slist.append("###   End species ###")
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
            _ls_splited = [x.split() for x in h.readlines()]

        elem = None
        tags = {}
        basis = []
        abf = []
        agt = cls.angular_grids_tag[0]

        i = -1
        headerl = []
        tier = -1
        is_aux = False
        enabled = True

        while i < len(_ls_splited) - 1:
            i += 1
            words = _ls_splited[i]
            l = " ".join(words)
            # print(words)
            # print(l, elem, l.startswith("species"))
            # header lines before species tag
            if elem is None and not l.startswith("species"):
                headerl.append(l)
            # skip when empty line
            if len(words) == 0:
                continue
            # skip when the line is a comment that do not involve basis set:
            if l.startswith('#'):
                if len(words) == 1:
                    tier = -1
                    continue
                if not l.startswith("# valence basis states") \
                        and (words[1] == "for_aux" or words[1] in cls.basis_types):
                    enabled = False
                    words = words[1:]
                    l = " ".join(words)
                else:
                    # check the tier information
                    # minimal basis functions
                    if l == "# Definition of \"minimal\" basis" \
                            or l.startswith("# ion occupancy") \
                            or l.startswith("# valence basis states") \
                            or l.startswith("# Necessary addition to the minimal basis"):
                        tier = 0
                        continue
                    # basis included as a tier
                    elif len(words) > 2:
                        l = l.replace("\"", "").replace("\'", "")
                        words = [x.lower() for x in l.split()]
                        tier_dict = {"first": 1, "second": 2, "third": 3, "fourth": 4, "fifth": 5}
                        if words[2] == "tier" and words[1] in tier_dict:
                            tier = tier_dict[words[1]]
                    # reset the tier after an irrelevant comment line
                    # this include the case "# Further basis functions"
                    else:
                        tier = -1
                    continue
            else:
                enabled = True
            tagk, tagv = l.split(maxsplit=1)
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
            elif tagk == "for_aux" or tagk in cls.basis_types:
                is_aux = False
                basis_key = "OBS"
                if tagk == 'for_aux':
                    is_aux = True
                    basis_key = "ABF"
                    tagk, tagv = tagv.strip().split(maxsplit=1)
                # now tagk should be one of the basis_types
                if tagk in cls.basis_types:
                    if tagk == 'gaussian':
                        vals = tagv.split()
                        # pGTO
                        if int(vals[1]) == 1:
                            new_basis = [tagk, tagv, is_aux, tier, enabled]
                        # cGTO
                        else:
                            # head plus the following vals[1] _ls
                            cgtos = [tagv,]
                            for x in _ls_splited[i + 1:i + 1 + int(vals[1])]:
                                cgtos.extend(x)
                            new_basis = [tagk, " ".join(cgtos), is_aux, tier, enabled]
                            i += int(vals[1])
                    else:
                        new_basis = [tagk, tagv, is_aux, tier, enabled]
                    basis.append(new_basis)
                    _logger.debug("append %s %s: %s", tagk, basis_key, new_basis)
                else:
                    info = "Unknown basis type {} on line {}, break for safety".format(tagk, i + 1)
                    _logger.error(info)
                    raise ValueError(info)
            else:
                info = "Unknown species tag {} on line {}, break for safety".format(tagk, i + 1)
                _logger.error(info)
                raise ValueError(info)
        if elem not in element_symbols[1:]:
            raise ValueError(f"Unknown element: {elem}")
        _logger.info("finished reading species file of element: %s, instantializing", elem)
        header = None
        if len(headerl) > 0:
            header = "\n".join(headerl)
        return cls(elem, tags, basis, header=header)

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
        pspecies = get_species_filepaths(directory, elem, species_defaults=species_defaults)[0]
        return cls.read(pspecies)
