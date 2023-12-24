# -*- coding: utf-8 -*-
"""FHI-aims related"""
import os
import pathlib
import json
from typing import Tuple, List, Dict, Union
from io import StringIO
from copy import deepcopy

import numpy as np

from mushroom.core.cell import Cell
from mushroom.core.ioutils import open_textio, get_banner, get_similar_str
from mushroom.core.logger import loggers

from mushroom.aims.species import Species

__all__ = [
    "read_geometry",
    "Control",
    "read_control"
]

_logger = loggers["aims"]

read_geometry = Cell.read_aims


def divide_control_lines(pcontrol: Union[str, os.PathLike]) -> List[List[str]]:
    """read and divide control file into general lines and species lines

    Args:
        pcontrol (pathlike)

    Returns:
        list. Each member is a list of str.
        The first is the lines of general and output setting.
        The reset are lines of the basis set setting for each species
    """
    specie_lines = []
    with open_textio(pcontrol, 'r') as h:
        lines = h.readlines()
        for i, l in enumerate(lines):
            if l.strip().startswith("species "):
                specie_lines.append(i)

    # no species lines are found, all lines are for general setting
    if len(specie_lines) == 0:
        return [lines,]

    divisions = [0, ]  # 0 for the general setting line
    # search backward to include the comment lines on top of species
    for isl, specie_line in enumerate(specie_lines):
        previous_specie = 0
        if isl != 0:
            previous_specie = specie_lines[isl - 1]
        for i in range(specie_line, previous_specie, -1):
            l = lines[i].strip()
            # empty line
            # TODO: filter out commented out basis set or general control line
            if not l.startswith("species") and not l.startswith("#") or i == previous_specie:
                divisions.append(i + 1)
                break
    regions = []
    for i, isl in enumerate(divisions):
        if i == 0:
            continue
        regions.append(lines[divisions[i - 1]:isl])
        if i == len(divisions) - 1:
            regions.append(lines[isl:])
    return regions


def get_path_ksymbols(ctrl_output_band: List) -> List[Union[str, None]]:
    """get the ksymbol list for band plot from the output band tag of a control object

    Args:
        ctrl_output_band (list): list of kpath segments, obtained by Control.get_output("band")
    """
    from mushroom.core.ioutils import greeks, greeks_latex

    if ctrl_output_band is None or len(ctrl_output_band) == 0:
        return []
    sym_ksegs = []
    for x in ctrl_output_band:
        ksym = x[3:5]
        for i in range(2):
            if ksym[i] in greeks:
                ksym[i] = greeks_latex[greeks.index(ksym[i])]
        sym_ksegs.append(ksym)
    # include the ends of first band
    sym = [*sym_ksegs[0]]
    # appending the left
    for st, ed in sym_ksegs[1:]:
        if st is None or ed is None:
            sym.append(None)
            continue
        if not st == sym[-1]:
            sym[-1] = f"{sym[-1]}|{st}"
        sym.append(ed)
    return sym


def _read_output_tags(lines):
    """read output tags in aims control file

    each element of lines is the text without output tag

    Note:
        For output tags like 'band', there can be multiple entries.
        Currently only 'band' of these tags are supported.
    """
    d = {}
    warn = "bad output tag line: %s"
    for l in lines:
        words = l.split(maxsplit=1)
        # single output keyword
        if len(words) == 1:
            tag, value = words[0], True
        else:
            tag, value = words
        if tag == 'band':
            d['band'] = d.get('band', [])
            value = value.split()
            if len(value) in [7, 9]:
                kpts = value[:6]
                try:
                    kseg = [kpts[:3], kpts[3:], int(value[6]), value[7], value[8]]
                except IndexError:
                    kseg = [kpts[:3], kpts[3:], int(value[6]), None, None]
                d['band'].append(kseg)
            else:
                _logger.warning(warn, l)
        else:
            d[tag] = value
    return d


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

    basic_tags_ref_json = os.path.join(os.path.dirname(__file__), "aims_tagsref.json")

    with open(basic_tags_ref_json, 'r') as h:
        basic_tags_ref = json.load(h)

    def __init__(self, tags: Dict = None, output_tags: Dict = None, species: List[Species] = None):
        self.tags = {}
        self.update_tags(tags)
        self.output = {}
        self.update_output_tags(output_tags)
        self.species = species
        self._if_species_changed = False
        self._elements = []
        if self.species is not None:
            self._elements = [s.elem for s in self.species]

    def __getitem__(self, key):
        return self.tags[key]

    def __setitem__(self, key, value):
        self.tags[key] = value

    def __delitem__(self, key):
        self.tags.pop(key)

    def copy(self):
        """copy the control"""
        return deepcopy(self)

    def get_species(self, elem: Union[int, str]) -> Species:
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
            sim_key = get_similar_str(tag, list(self.tags.keys()))
            if sim_key is None:
                raise KeyError(f"no tag {tag} is found in control")
            else:
                raise KeyError(f"no tag {tag} is found in control, do you mean '{sim_key}'?")

    # pylint: disable=W0707
    def get_output(self, tag, *default):
        """get the value of tag"""
        try:
            return self.output[tag]
        except KeyError:
            if default:
                return default[0]
            raise KeyError(f"no output tag {tag} is found in control")

    def update_tag(self, tag: str, value: str):
        """update the value of tag

        Args:
            tag (str): the tag to be updated
            value (str-able): the new value of the tag
                If set to None, the tag will be deleted
        """
        if value is None:
            try:
                _logger.debug("removed tag '%s', original value: %s", tag, self.tags.pop(tag))
            except KeyError:
                _logger.debug("tag '%s' to remove is not defined, skip", tag)
            return
        if value is True or value is False:
            try:
                v = {True: ".true.", False: ".false."}.get(value, str(value))
                self.tags[tag] = v
                _logger.debug("bool tag '%s' updated to: %s", tag, v)
            except ValueError as _e:
                raise ValueError(f"cannot turn value into string: {value}") from _e
        else:
            try:
                self.tags[tag] = value
                _logger.debug("tag '%s' updated to: %s", tag, self.tags[tag])
            except ValueError as _e:
                raise ValueError(f"cannot turn value into string: {value}") from _e

    def update_tags(self, tags: dict):
        """collective update tag values"""
        for k, v in tags.items():
            self.update_tag(k, v)

    def update_output_tag(self, output_tag, value):
        """update the output tag value

        Args:
            output_tag (str): the output tag to be updated
            value: the new value of the output tag
                set to None to delete the tag
        """
        if value is None:
            try:
                _logger.debug("removed output 'tag' %s, original value: %s", output_tag,
                              self.output.pop(output_tag))
            except KeyError:
                _logger.debug("output tag '%s' to remove is not defined, skip", output_tag)
            return
        self.output[output_tag] = value

    def update_output_tags(self, output_tags: Dict):
        """collective update output tag values"""
        for k, v in output_tags.items():
            self.update_output_tag(k, v)

    def update_species_basic_tag(self, elem, tag, value):
        """update the species basic tag of element ``elem``

        Args:
            elem (str or int): name of element, or its index in the control
            tag (str): the species basic tag
            value : the new value of tag. See ``update_basic_tag``
        """
        self.get_species(elem).update_basic_tag(tag, value)

    def get_basis(self, elem, *args, **kwargs):
        """get the basis of element ``elem``

        Args:
            elem (str or int): name of element, or its index in the control
            args and kwargs: parsed to the Species.get_basis method
        """
        return self.get_species(elem).get_basis(*args, **kwargs)

    def get_abf(self, elem, *args, **kwargs):
        """get the abf of element ``elem``

        Args:
            elem (str or int): name of element, or its index in the control
            args and kwargs: parsed to the Species.get_abf method
        """
        return self.get_species(elem).get_abf(*args, **kwargs)

    def add_basis(self, elem, *args, **kwargs):
        """add basis to speices of element ``elem``

        Args:
            elem (str or int): name of element, or its index in the control
            args and kwargs: parsed to the Species.add_basis method
        """
        self.get_species(elem).add_basis(*args, **kwargs)

    def add_abf(self, elem, *args, **kwargs):
        """add abf to speices of element ``elem``

        Args:
            elem (str or int): name of element, or its index in the control
            args and kwargs: parsed to the Species.add_abf method
        """
        self.get_species(elem).add_abf(*args, **kwargs)

    def modify_basis(self, elem, *args, **kwargs):
        """modify basis in speices of element ``elem``

        Args:
            elem (str or int): name of element, or its index in the control
            args and kwargs: parsed to the Species.modify_basis method
        """
        self.get_species(elem).modify_basis(*args, **kwargs)

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

    def purge_species(self):
        """remove all species"""
        self.species = []
        self._if_species_changed = True

    def replace_specie(self, specie_new):
        """replace specie of element with a new one ``specie_new``"""
        info = f"{specie_new.elem} is not included in species"
        if specie_new.elem in self.elements:
            self.species[self.elements.index(specie_new.elem)] = specie_new
            self._if_species_changed = True
        else:
            _logger.warning("%s, no replace", info)

    def add_species(self, *ss, error_replace: bool = True):
        """add species to the control file"""
        for s in ss:
            info = f"{s.elem} is already included in species"
            if s.elem in self.elements:
                if error_replace:
                    raise ValueError(info)
                _logger.warning("%s, will replace", info)
                self.replace_specie(s)
            else:
                if self.species is None:
                    self.species = []
                self.species.append(s)
            self._if_species_changed = True

    def add_default_species(self, directory: str, *elems,
                            error_replace: bool = True,
                            species_defaults: str = None):
        """add species to the control file"""
        ss = [Species.read_default(elem, directory=directory) for elem in elems]
        self.add_species(*ss, error_replace=error_replace)

    def _export_basic_tags(self):
        """export basic tags into a list of string for later process"""
        slist = []
        tags_local = deepcopy(self.tags)
        # export by group
        for group in self.basic_tags_ref.values():
            tags = {}
            for tag in group["tags"].keys():
                if tag in tags_local.keys():
                    tags[tag] = tags_local.pop(tag)
            if tags.keys():
                slist.append("# " + group["section"])
                slist.extend(f"{k} {v}" for k, v in tags.items())
                slist.append("")
        if tags_local.keys():
            slist.append("# Unrecognized tags")
            slist.extend(f"{k} {v}" for k, v in tags_local.items())
            slist.append("")
        return slist

    def _export_output_tags(self):
        """export output tags into a list of string for later process"""
        slist = []
        if self.output.items():
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
        slist.append("")
        return slist

    def export(self):
        """export the control object to a string"""
        # General tags
        slist = [get_banner("General Basic Tags"), ]
        slist.extend(self._export_basic_tags())

        # Output tags
        slist.append(get_banner("Output Tags"))
        slist.extend(self._export_output_tags())

        # Basis sets
        slist.append(get_banner("Basis Sets"))
        slist.append("")
        slist.extend(s.export() + "\n" for s in self.species)

        return slist

    def __str__(self):
        return "\n".join(self.export())

    def write(self, pcontrol):
        """write the control content to file ``pcontrol``"""
        if len(self.species) == 0:
            _logger.warning("Writing control to file %s with no species info!" % pcontrol)
        with open_textio(pcontrol, 'w') as h:
            print(self.__str__(), file=h)

    @classmethod
    def read(cls, pcontrol: Union[str, os.PathLike] = "control.in"):
        """Read aims control file and return a control object

        Note that global flags after species are excluded and all the comment are removed.
        """
        _logger.info("Reading control file: %s", pcontrol)

        regions = divide_control_lines(pcontrol)
        tags_lines = regions[0]
        lines_species_all = regions[1:]

        if len(lines_species_all) == 0:
            _logger.warning("No species tag is found in control")
        else:
            for lines_specie in lines_species_all:
                for line in lines_specie:
                    l = line.strip()
                    if l.startswith("speices"):
                        _logger.debug("Detected species: %r", l.split()[1])
                        break

        # read all species information
        # delegate the reading to the Species object
        species = []
        for lines_specie in lines_species_all:
            species.append(Species.read(StringIO(("".join(lines_specie)).strip())))

        tags = {}
        output = []
        # read general tags and output tags
        i = 0
        while i < len(tags_lines):
            l = tags_lines[i].strip()
            if l.startswith("#") or len(l) == 0:
                i += 1
                continue
            tagkv = l.split(maxsplit=1)
            if len(tagkv) > 1:
                tagk, tagv = tagkv[0], tagkv[1]
            else:
                tagk = tagkv[0]
                tagv = None
            if tagk == 'output':
                if tagv is None:
                    _logger.warning("empty output tag, ignore")
                else:
                    output.append(tagv)
            else:
                # single keyword without value
                # NOTE I am not sure if there is any single keyword without value in aims,
                #      though put here for safety
                if tagv is None:
                    tagv = ".true."
                else:
                    tagv = tagkv[1]
                tags[tagk] = tagv
            i += 1
        output = _read_output_tags(output)
        _logger.debug("tags: %r", tags)
        _logger.debug("output: %r", output)
        _logger.debug("species: %r", species)
        return cls(tags, output, species)


def read_control(pcontrol: str = "control.in") -> Control:
    """Read in a control.in file

    Args:
        pcontrol (str): path to the control file

    Returns:
        Control object
    """
    return Control.read(pcontrol)

