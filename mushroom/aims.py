# -*- coding: utf-8 -*-
"""FHI-aims related"""
from typing import Tuple, List
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
    """aims control file

    Note that global flags after species are excluded.
    """

    species_subtag = ["nucleus", "mass", "l_hartree", "cut_pot", "basis_dep_cutoff", "radial_base",
                      "radial_multiplier",
                      "angular_grids", "division", "outer_grid",
                      "angular_min",]
    basis_tag = ["hydro", "ion_occ", "valence", "ionic"]
    abf_tag = ["for_aux"]

    def __init__(self, pcontrol="control.in"):
        def _read_species_block(lines):
            """read in species block"""
            # TODO handling basis construction
            elem = lines[0].split()[1]
            d = {}
            return {elem: d}
        def _read_output(lines):
            """read output tags"""
            d = {}
            for t in lines:
                if len(t) == 0:
                    _logger.warning("detect empty output tag")
                    continue
                if len(t) == 1:
                    d[t[0]] = True
                elif len(t) == 2:
                    d[t[0]] = t[1]
                else:
                    if t[0] == 'band':
                        d['band'] = d.get('band', [])
                        d['band'].append(t[1:])
                    else:
                        d[t[0]] = t[1:]
            return d

        _logger.info("Reading control file: %s", pcontrol)
        _ls = readlines_remove_comment(pcontrol, keep_empty_lines=False, trim_leading_space=True)
        # original lines
        self._lines = _ls
        self.tags = {}
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

        # read other global setup
        i = 0
        output = []
        while i < len(_ls[:species_region[0]]):
            tagv = _ls[i].split()
            tag = tagv[0]
            tagv = tagv[1:]
            i += 1
            if tag == 'output':
                output.append(tagv)
                continue
            if len(tagv) == 1:
                self.tags[tag] = tagv[0]
            else:
                self.tags[tag] = tagv

        self.tags["species"] = species
        self.tags["output"] = _read_output(output)

