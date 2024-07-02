# -*- coding: utf-8 -*-
"""Utilities for LibRPA"""
import numpy as np
from io import StringIO

from mushroom.core.logger import loggers

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
