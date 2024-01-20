# -*- coding: utf-8 -*-
"""Utilites related to GW in FHI-aims"""
import os
import re
import numpy as np

__all__ = [
    "read_aims_self_energy_dir"
]


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

        matched = re.fullmatch(r"Sigma\.omega\.n_(\d+)\.k_(\d+)\.dat", fn)
        if matched is not None:
            n = int(matched.group(1))
            s = 1
            k = int(matched.group(2))
            data_dict_kgrid[(s - 1, k - 1, n - 1)] = sigc
            continue
        matched = re.fullmatch(r"Sigma\.omega\.n_(\d+)\.s_(\d+)\.k_(\d+)\.dat", fn)
        if matched is not None:
            n = int(matched.group(1))
            s = int(matched.group(2))
            k = int(matched.group(3))
            data_dict_kgrid[(s - 1, k - 1, n - 1)] = sigc
            continue
        matched = re.fullmatch(r"Sigma\.omega\.n_(\d+)\.band_(\d+)\.k_(\d+)\.dat", fn)
        if matched is not None:
            n = int(matched.group(1))
            s = 1
            kp = int(matched.group(2))
            k = int(matched.group(3))
            data_dict_band[(s - 1, kp - 1, k - 1, n - 1)] = sigc
            continue
        matched = re.fullmatch(r"Sigma\.omega\.n_(\d+)\.s_(\d+)\.band_(\d+)\.k_(\d+)\.dat", fn)
        if matched is not None:
            n = int(matched.group(1))
            s = int(matched.group(2))
            kp = int(matched.group(3))
            k = int(matched.group(4))
            data_dict_band[(s - 1, kp - 1, k - 1, n - 1)] = sigc
            continue

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
