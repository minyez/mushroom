# -*- coding: utf-8 -*-
"""FHI-aims related"""
import os
import pathlib
from typing import Tuple, List, Dict, Union
from io import StringIO
from copy import deepcopy

import numpy as np

from mushroom.core.cell import Cell
from mushroom.core.ioutils import readlines_remove_comment, grep, open_textio, greeks, greeks_latex
from mushroom.core.logger import loggers

from mushroom.aims.species import Species

__all__ = [
    "read_geometry",
    "Control",
    "read_control"
]

_logger = loggers["aims"]

read_geometry = Cell.read_aims


def read_divide_control_lines(pcontrol):
    """read and divide control file into general lines and species lines

    Args:
        pcontrol (pathlike)

    Returns:
        two list of str
    """
    first_specie_line = None
    with open_textio(pcontrol, 'r') as h:
        lines = h.readlines()
        for i, l in enumerate(lines):
            if l.strip().startswith("species    "):
                first_specie_line = i
                break

    # no species lines are found
    if first_specie_line is None:
        return lines, []

    general_l = []
    species_l = lines
    # include the comment lines on top of species
    for i in range(first_specie_line - 1, 0, -1):
        l = lines[i].strip()
        if not l.startswith("#"):
            general_l = lines[:i + 1]
            species_l = lines[i + 1:]
            break
    return general_l, species_l


def handle_control_ksymbol(pcontrol: str) -> List:
    """get the ksymbol list from the control file

    Args:
        pcontrol (str): path to the control file"""
    c = Control.read(pcontrol)
    bands = c.get_output("band", [])
    if not bands:
        raise ValueError(f"control containing no output band tag: {pcontrol}")
    sym_ksegs = []
    for x in bands:
        ksym = x[3:5]
        for i in range(2):
            if ksym[i] in greeks:
                ksym[i] = greeks_latex[greeks.index(ksym[i])]
        sym_ksegs.append(ksym)
    err = ValueError("ksymbols in control are incomplete! use --sym option instead")
    sym = [*sym_ksegs[0]]
    if None in sym:
        raise err
    for st, ed in sym_ksegs[1:]:
        if st is None or ed is None:
            raise err
        if not st == sym[-1]:
            sym[-1] = f"{sym[-1]}|{st}"
        sym.append(ed)
    # print(f"Extracted symbols: {sym}")
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

    def __init__(self, tags: Dict = None, output: Dict = None, species: List[Species] = None):
        self.tags = tags
        self.output = output
        self.species = species
        self._if_species_changed = False
        if self.species is not None:
            self._elements = [s.elem for s in self.species]

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
        if value is None:
            try:
                _logger.info("removed tag '%s', original value: %s", tag, self.tags.pop(tag))
            except KeyError:
                _logger.info("tag '%s' to remove is not defined, skip", tag)
            return
        if value is True or value is False:
            try:
                v = {True: ".true.", False: ".false."}.get(value, str(value))
                self.tags[tag] = v
                _logger.info("bool tag '%s' updated to: %s", tag, v)
            except ValueError as _e:
                raise ValueError(f"cannot turn value into string: {value}") from _e
        else:
            try:
                self.tags[tag] = value
                _logger.info("tag '%s' updated to: %s", tag, self.tags[tag])
            except ValueError as _e:
                raise ValueError(f"cannot turn value into string: {value}") from _e

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
            except KeyError:
                _logger.info("output tag '%s' to remove is not defined, skip", output_tag)

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

    def add_species(self, *ss, error_replace=True):
        """add species to the control file"""
        for s in ss:
            info = f"{s.elem} is already included in species"
            if s.elem in self.elements:
                if error_replace:
                    raise ValueError(info)
                _logger.warning("%s, will replace", info)
                self.replace_specie(s)
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
        return slist

    def write(self, pcontrol):
        """write the control content to file ``pcontrol``"""
        with open_textio(pcontrol, 'w') as h:
            print("\n".join(self.export()), file=h)

    @classmethod
    def read(cls, pcontrol: str = "control.in"):
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
            ed = species_region[i + 1]
            species.append(Species.read(StringIO("\n".join(_ls[st:ed]))))

        # read other setup, including general tags and output tags
        i = 0
        output = []
        while i < len(_ls[:species_region[0]]):
            tagkv = _ls[i].split(maxsplit=1)
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

