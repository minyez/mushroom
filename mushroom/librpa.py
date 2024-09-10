# -*- coding: utf-8 -*-
"""Utilities for LibRPA"""
import os
import re
from io import StringIO
from typing import Union

import numpy as np

from mushroom.core.ioutils import open_textio
from mushroom.core.logger import loggers
from mushroom.core.bs import BandStructure

_logger = loggers["librpa"]


def read_self_energy_imagfreq(fn: str):
    """Read self energy on imaginary frequency from data file ``fn``

    Args:
        fn (str) : path to the data file

    Returns:
        2 nd-array. The first is 1d array containing the (imaginary) frequency points.
        The second is 4d array, (nfreq, nspin, nkpts, nstates) containing the
        correlation self energy data
    """
    omegas = None
    data = None

    with open(fn, 'r') as h:
        lines = h.readlines()
    nfreqs, nspins, nkpts, nstates = map(int, lines[0].split())

    _logger.info("Sigma dimension, nfreq, nspin, nkpsts, nstates: %d %d %d %d",
                 nfreqs, nspins, nkpts, nstates)

    omegas = np.loadtxt(StringIO("".join(lines[1:1 + nfreqs])))
    data_re, data_im = np.loadtxt(StringIO("".join(lines[1 + nfreqs:])), unpack=True)
    data = data_re + 1.0j * data_im
    data = data.reshape(nspins, nkpts, nstates, nfreqs)
    # move the nfreqs axis to the first
    data = np.rollaxis(data, 3, 0)

    return omegas, data


def read_quasi_particle_energies_stdout(fn: Union[str, os.PathLike] = "librpa.out",
                                        kind: str = "qp",
                                        **kwargs):
    """Read QP energies from standard output

    Args:
        fn (str): path to LibRPA standard output
        kind (str): any of "qp", "ks", and "exx"

        Other keywords arguments are parsed to the ``BandStructure`` class.

    Returns:
        BandStructure object, k-points (in fractional coordinates)
    """
    nspins = None
    nkpts = None
    nstates = None
    i_qpe_headlines = []
    ispins = []
    ikpts = []
    kpoints = []

    with open_textio(fn, 'r') as h:
        lines = h.readlines()

    # spin  1, k-point    1: (0.00000, 0.00000, 0.00000)
    pattern = re.compile(r"^spin\s+(\d+), k-point\s+(\d+): \(([-\d.]+), ([-\d.]+), ([-\d.]+)\)")

    for i, l in enumerate(lines):
        m = re.match(pattern, l)
        if m is not None:
            i_qpe_headlines.append(i)
            ispins.append(int(m.group(1)))
            ikpts.append(int(m.group(2)))
            kpt = tuple([float(m.group(3)), float(m.group(4)), float(m.group(5))])
            kpoints.append(kpt)

    if len(i_qpe_headlines) == 0:
        raise ValueError("QP energies results are not available from output: %r" % fn)

    # prune previous lines
    i_qpe_headlines = np.array(i_qpe_headlines)
    lines = lines[i_qpe_headlines[0]:]
    i_qpe_headlines -= i_qpe_headlines[0]

    # get the number of k-points and spins by checking the available output lines
    nspins = np.max(ispins)
    nkpts = np.max(ikpts)
    kpoints = np.array(kpoints)
    if nkpts > 1:
        nstates = i_qpe_headlines[1] - i_qpe_headlines[0] - 5
    else:
        for i, l in enumerate(lines):
            if l.strip() == "":
                nstates = i - 4
                break
    _logger.info("QPE dimensions, nspin, nkpsts, nstates: %d %d %d",
                 nspins, nkpts, nstates)

    qpe_lines = []
    for i in i_qpe_headlines:
        qpe_lines.extend(lines[i + 4:i + 4 + nstates])
    occ, eks, vxc, vex, eqp = np.loadtxt(StringIO("".join(qpe_lines)), usecols=[1, 2, 3, 4, -1], unpack=True)
    occ = np.reshape(occ, (nspins, nkpts, nstates))
    eks = np.reshape(eks, (nspins, nkpts, nstates))
    vxc = np.reshape(vxc, (nspins, nkpts, nstates))
    vex = np.reshape(vex, (nspins, nkpts, nstates))
    eqp = np.reshape(eqp, (nspins, nkpts, nstates))
    if kind in ["e_qp", "qp"]:
        bs = BandStructure(eqp, occ, **kwargs)
    elif kind in ["e_ks", "e_mf", "ks", "mf"]:
        bs = BandStructure(eks, occ, **kwargs)
    elif kind in ["e_hf", "hf", "exx"]:
        bs = BandStructure(eks - vxc + vex, occ, **kwargs)
    else:
        raise ValueError("kind %s not supported, use any of following: ks, qp, exx" % kind)
    return bs, kpoints
