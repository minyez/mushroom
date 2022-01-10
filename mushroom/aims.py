# -*- coding: utf-8 -*-
"""FHI-aims related"""
from typing import Tuple, List, Dict
import numpy as np

from mushroom.core.logger import create_logger
from mushroom.core.typehint import RealVec3D
from mushroom.core.bs import BandStructure
from mushroom.core.ioutils import readlines_remove_comment, grep

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
    except IndexError as err:
        raise ValueError("bad input string for aims band energy: {}".format(bstr)) from err

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
    Value of output tags are

    Args:
        general (dict)
        output (dict)
    """

    species_subtag = ["nucleus", "mass", "l_hartree", "cut_pot", "basis_dep_cutoff", "radial_base",
                      "radial_multiplier",
                      "angular_grids", "division", "outer_grid",
                      "angular_min",]
    basis_tag = ["hydro", "ion_occ", "valence", "ionic"]
    abf_tag = ["for_aux"]

    def __init__(self, tags: Dict = None, output: Dict = None, species: Dict = None):
        self.tags = tags
        self.output = output
        self.species = species

    @classmethod
    def read(cls, pcontrol="control.in"):
        """Read aims control file and return an control object

        Note that global flags after species are excluded.
        """
        def _read_species_block(lines):
            """read in species block"""
            # TODO handling basis construction
            elem = lines[0].split()[1]
            d = {}
            return {elem: d}
        def _read_output(lines):
            """read output tags

            each element of lines is (linenum, linetext)"""
            d = {}
            warn = "bad output tag on line %"
            for i, l in lines:
                words = l.split()
                otag, ovalue = words[0], words[1:]
                if not ovalue:
                    d[otag] = True
                elif len(words) == 1:
                    d[otag] = words[1]
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
                            _logger.warning(warn, i)
                    else:
                        d[otag] = ovalue
            return d

        _logger.info("Reading control file: %s", pcontrol)
        _ls = readlines_remove_comment(pcontrol, keep_empty_lines=False, trim_leading_space=True)
        tags = {}
        # line number of each specie header
        species_ln = grep(r'species', _ls, return_linenum=True)
        if species_ln[1]:
            for s, i in zip(*species_ln):
                _logger.debug("- species line %4d: %s", i+1, s.split()[1:])
        else:
            _logger.warning("No species tag is found in control")

        # read all species information
        species_region = [*species_ln[1], len(_ls)]
        species = {}
        for i, st in enumerate(species_region[:-1]):
            ed = species_region[i+1]
            species.update(_read_species_block(_ls[st:ed]))

        # read other setup, including general tags and output tags
        i = 0
        output = []
        while i < len(_ls[:species_region[0]]):
            tagkv = _ls[i].split(maxsplit=1)
            tagk, tagv = tagkv[0], tagkv[1:]
            if tagk == 'output':
                if not tagv:
                    _logger.warning("empty output tag on line: %d", i+1)
                else:
                    # add line number for debugging
                    output.append((i+1, tagkv[1]))
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

