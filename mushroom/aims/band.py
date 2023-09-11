# -*- coding: utf-8 -*-
"""utilities for parsing standard output of FHI-aims"""
from typing import Tuple, List

from mushroom.core.typehint import RealVec3D
from mushroom.core.bs import BandStructure


def read_band_output(
        bfile,
        *bfiles,
        filter_k_before: int = 0,
        filter_k_behind: int = None,
        unit: str = 'ev') -> Tuple[BandStructure, List[RealVec3D]]:
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


def handle_single_band_mulliken_output(bfile):
    """process a single bandmlk file

    Args:
        bfile (str): path to bandmlk file

    Returns:
        ndarray (kpts), ndarray (band energy), ndarray (occupation), ndarray (mulliken)
    """
    _logger.debug("handling band mulliken file: %r", bfile)
    with open(bfile, 'r') as h:
        lines = h.readlines()
    # match lines like the following:
    # k point number:     1: (   0.50000000   0.50000000   0.50000000 )
    kpts_pattern = r'^k point number:\s+\d+: \(' + r'(\s+[+-]?\d\.\d+)' * 3 + r'\s+\)'
    kpts_groups = grep(kpts_pattern, lines, return_group=True)
    kpts = [[float(m.group(1)), float(m.group(2)), float(m.group(3))] for m in kpts_groups]
    # NOTE: there is some error in kpoint coordinate
    # could potentially affect the determination of path segments
    # in this case, one need to round numbers to ~7 digits after
    # converting to ndarray
    kpts = np.array(kpts)
    # filter out the kpoint and explanation lines
    lines = [x for x in lines if not (x.startswith("k point") or x.startswith("    State"))]

    nkpts = len(kpts)
    nbands = int(lines[-1].split()[0])
    natms = len(lines) // nkpts
    if natms % nbands != 0:
        raise ValueError("invalid bandmlk file")
    natms = natms // nbands
    _logger.debug("dimension detected (nkpts %d, nbands %d, natms %d)",
                  nkpts, nbands, natms)

    # check the largest number of angular momentum quantum number among atoms
    # 5 accounts for state, ene, occ, atom index, total
    # 1 considers maxl of "s" is 0
    maxl = max(len(x.split()) for x in lines[3:3 + natms]) - 5 - 1
    ene_occ = [x.split()[1:3] for x in lines[::natms]]
    ene = np.array([float(x[0]) for x in ene_occ]).reshape(nkpts, nbands)
    occ = np.array([float(x[1]) for x in ene_occ]).reshape(nkpts, nbands)
    # starting from the s component
    mlk_str = [list(map(float, x.split()[5:])) for x in lines]
    maxl_per_line = [len(x) - 1 for x in mlk_str]
    for i, l in enumerate(maxl_per_line):
        if l < maxl:
            line = [0.0, ] * (maxl + 1)
            line[:l + 1] = mlk_str[i]
            mlk_str[i] = line
    mlk = np.array(mlk_str).reshape(nkpts, nbands, natms, maxl + 1)
    if np.min(mlk) < -0.1:
        _logger.warning("significant (<-0.1) negative mulliken charge found in %s", bfile)

    return kpts, ene, occ, mlk


def read_band_mulliken_output(
        bfile,
        *bfiles,
        filter_k_before: int = 0,
        filter_k_behind: int = None,
        unit: str = 'ev') -> Tuple[BandStructure, List[RealVec3D]]:
    """read band mulliken output files and return a Band structure object

    Note that all band energies are treated in the same spin channel,
    the resulting ``BandStructure`` object always has nspins=1

    Args:
        bfile (str)
        unit (str): unit of energies, default to ev

    Returns:
        BandStructure, k-points
    """
    kpts, ene, occ, mlk = handle_single_band_mulliken_output(bfile)
    _, nbands, natms, nprjs = mlk.shape
    for bf in bfiles:
        kpts1, ene1, occ1, mlk1 = handle_single_band_mulliken_output(bf)
        _, nbands1, natms1, nprjs1 = mlk1.shape
        if nbands1 != nbands or natms1 != natms or nprjs1 != nprjs:
            raise ValueError("Inconsitent shape found when reading bandmlk: %s" % bf)
        kpts = np.concatenate((kpts, kpts1))
        ene = np.concatenate((ene, ene1))
        occ = np.concatenate((occ, occ1))
        mlk = np.concatenate((mlk, mlk1))

    nkpts_total = len(kpts)
    if filter_k_behind is None:
        filter_k_behind = nkpts_total
    kpts = kpts[filter_k_before:filter_k_behind, :]
    occ = occ.reshape(1, nkpts_total, nbands)[:, filter_k_before:filter_k_behind, :]
    ene = ene.reshape(1, nkpts_total, nbands)[:, filter_k_before:filter_k_behind, :]
    mlk = mlk.reshape(1, nkpts_total, nbands, natms, nprjs)[:, filter_k_before:filter_k_behind, :, :, :]
    # NOTE: the atomic projectors are assumed sequential, i.e. s, p, d, f, ...
    return BandStructure(ene, occ, pwav=mlk, unit=unit, prjs=l_channels[:nprjs]), kpts

