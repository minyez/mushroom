# -*- coding: utf-8 -*-
"""Utilites related to GW in FHI-aims"""
import os
import re
import numpy as np

from mushroom.core.logger import loggers

__all__ = [
    "read_aims_self_energy_dir"
]

_logger = loggers["aims"]


def _read_aims_single_sigc_dat(sigcdat_fn):
    """read single sigc.dat file to get correlation self-energy

    Args:
        sigcdat_fn (path-like)

    Retunrs:
        Two nd-array: 1d real array for frequencies, 1d complex array for self-energy
    """
    omegas = []
    sigc = []
    with open(sigcdat_fn, 'r') as h:
        for line in h.readlines():
            try:
                omega, reval, imval = line.split()
            # very large number such that there leaves no space between values
            except ValueError:
                try:
                    omega, reval, imval = line.split()[0], 0.0, 0.0
                except ValueError:
                    raise ValueError("Fail to read {}".format(sigcdat_fn))
            omegas.append(float(omega))
            sigc.append(float(reval) + 1j * float(imval))
    return omegas, sigc


def _fullmatch_nsbk_file_name(fn: str, prefix: str, suffix: str):
    """

    Args:
        fn (str): filename to match
        prefix (str): prefix to the pattern
        suffix (str): suffix to the pattern

    Returns:
        4 integer or None, istate, ispin, iband, ikpoint, starting from 0
    """
    patterns = (
        (prefix + r"n_(\d+)\.k_(\d+)" + suffix, (1, "1", None, 2)),
        (prefix + r"n_(\d+)\.s_(\d+)\.k_(\d+)" + suffix, (1, 2, None, 3)),
        (prefix + r"n_(\d+)\.band_(\d+)\.k_(\d+)" + suffix, (1, "1", 2, 3)),
        (prefix + r"n_(\d+)\.s_(\d+)\.band_(\d+)\.k_(\d+)" + suffix, (1, 2, 3, 4)),
    )
    rets = []
    for pattern, groups in patterns:
        matched = re.fullmatch(pattern, fn)
        if matched is None:
            continue
        for group in groups:
            if group is None:
                rets.append(None)
            if isinstance(group, str):
                rets.append(int(group) - 1)
            if isinstance(group, int):
                rets.append(int(matched.group(group)) - 1)
        break
    return rets


def read_aims_self_energy_dir(sedir: str = "self_energy"):
    """read all sigc data in self energy directory `sedir`

    Args:
        sedir (path-like)

    Returns:
        1d array: frequencies
        integer: index of the first state
        4d array: sigc data on kgrid, (freq, spin, kpoint, state)
        a list of 4d-arrays: sigc data along band paths, (freq, spin, kpoint, state)
    """
    data_dict_kgrid = {}
    data_dict_band = {}
    omegas = []

    nkpts = 0
    nstates = 0

    for sigc_path in os.listdir(sedir):
        omegas, sigc = _read_aims_single_sigc_dat(os.path.join(sedir, sigc_path))
        fn = os.path.basename(sigc_path)

        try:
            n, s, kp, k = _fullmatch_nsbk_file_name(fn, r"Sigma\.omega\.", r"\.dat")
            if kp is None:
                data_dict_kgrid[(s, k, n)] = sigc
            else:
                data_dict_band[(s, kp, k, n)] = sigc
        except ValueError:
            _logger.warn("invalid self energy data file: %s", sigc_path)

    # assume all files have the same frequencies (should be the case)
    nomegas = len(omegas)

    nkpts_grid = 0
    if data_dict_kgrid:
        nspins = max([x for x, _, _ in data_dict_kgrid.keys()]) + 1
        nkpts_grid = max([x for _, x, _ in data_dict_kgrid.keys()]) + 1
        state_low = min([x for _, _, x in data_dict_kgrid.keys()])
        state_high = max([x for _, _, x in data_dict_kgrid.keys()])
    else:
        try:
            nspins = max([x for x, _, _, _ in data_dict_band.keys()]) + 1
        except ValueError:
            raise ValueError("Cannot determine nspins")
        state_low = min([x for _, _, _, x in data_dict_band.keys()])
        state_high = max([x for _, _, _, x in data_dict_band.keys()])

    # not all states are calculated, get it from the indices of lowest and highest state
    nstates = state_high - state_low + 1

    data_kgrid = np.zeros((nomegas, nspins, nkpts_grid, nstates), dtype='complex64')
    for (isp, ik, istate), sigc_freq in data_dict_kgrid.items():
        data_kgrid[:, isp, ik, istate - state_low] = sigc_freq[:]

    nkpaths = 0
    if data_dict_band:
        nkpaths = max([x for _, x, _, _ in data_dict_band.keys()]) + 1
    # Assume nomegas, nspins and nstates are the same as in the kgrid calculation
    # Further, since each band path can have different number of kpoints,
    # we export a list instead of a single 5d array
    data_bands = []
    for ikpath in range(nkpaths):
        nkpts_band = max([x for _, ikp, x, _ in data_dict_band.keys() if ikp == ikpath]) + 1
        data_band = np.zeros((nomegas, nspins, nkpts_band, nstates), dtype='complex64')
        for (isp, ikp, ik, istate), sigc_freq in data_dict_band.items():
            if ikp != ikpath:
                continue
            data_band[:, isp, ik, istate - state_low] = sigc_freq[:]
        data_bands.append(data_band)

    return omegas, state_low, data_kgrid, data_bands


def _read_aims_single_specfunc_dat(specfuncdat_fn, unit: str = "ev"):
    """read single spectral function data file "spectral_function.dat" in 'spectral_function/' directory

    Args:
        sigcdat_fn (path-like)
        unit (str): "ev" or "au", unit to export

    Retunrs:
        float: Kohn-Sham eigenvalue
        float:
        nd-array: 1d real array for frequencies
        nd-array: 1d real array for real-part of self-energy
        nd-array: 1d real array for imag-part of self-energy
        nd-array: 1d real array for spectral function
    """
    from mushroom.core.constants import HA2EV

    assert unit in ["ev", "au"]

    with open(specfuncdat_fn, 'r') as h:
        eKS = float(h.readline().split()[1])
        eQP_wo_c = float(h.readline().split()[1])
        unit_file = "ev"
        if "Ha" in h.readline():
            unit_file = "au"

    omegas, real_part, imag_part, specfunc = np.loadtxt(specfuncdat_fn, usecols=[0, 1, 2, 3], unpack=True)

    conv = None
    if unit != unit_file:
        conv = HA2EV
        if unit == "ha":
            conv = 1.0 / conv

    if conv is not None:
        omegas *= conv
        eKS *= conv
        eQP_wo_c *= conv
        real_part *= conv
        imag_part *= conv
        specfunc /= conv

    return eKS, eQP_wo_c, omegas, real_part, imag_part, specfunc
