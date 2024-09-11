# -*- coding: utf-8 -*-
"""Utilites related to GW in FHI-aims"""
import os
import re
import struct
from typing import Callable, Union
from concurrent.futures import ProcessPoolExecutor, as_completed

import numpy as np

from mushroom.core.logger import loggers

__all__ = [
    "read_aims_self_energy_dir",
    "read_aims_self_energy_restart_file"
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


def fullmatch_nsbk_file_name(fn: str, prefix: str, suffix: str):
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


def get_nsbk_filename_pattern(prefix, suffix,
                              istate: Union[int, str] = None,
                              ispin: int = None,
                              iband: Union[int, str] = None,
                              ikpt: Union[int, str] = None,
                              spin_polarized: bool = False, out_band: bool = False):
    middle_pattern = []

    if istate is None:
        middle_pattern.append(r"n_(\d+)")
    else:
        try:
            middle_pattern.append(r"n_{:d}".format(int(istate) + 1))
        except ValueError:
            middle_pattern.append(r"n_{}".format(istate))

    if ispin is None:
        if spin_polarized:
            middle_pattern.append(r"s_(\d+)")
    else:
        if ispin > 0 and spin_polarized:
            middle_pattern.append(r"s_{:d}".format(ispin + 1))

    if iband is None:
        if out_band:
            middle_pattern.append(r"band_(\d+)")
    else:
        try:
            middle_pattern.append(r"band_{:d}".format(int(iband) + 1))
        except ValueError:
            middle_pattern.append(r"band_{}".format(iband))

    if ikpt is None:
        middle_pattern.append(r"k_(\d+)")
    else:
        try:
            middle_pattern.append(r"k_{:d}".format(int(ikpt) + 1))
        except ValueError:
            middle_pattern.append(r"k_{}".format(ikpt))
    return prefix + r"\.".join(middle_pattern) + suffix


def get_nsbk_filename(prefix, suffix, istate: int, ikpt: int, ispin: int = None, iband: int = None,
                      spin_polarized: bool = False):
    """Read a single n.s.b.k file

    Args:
        ispin (int): 0 or 1.
           If ispin is 0 and spin_polarized is False, the file is treated from non-spin-polarization calculation.
           Otherwise it is spin polarized.
    """
    middle = ["n_{:d}".format(istate + 1)]
    if ispin is not None and (ispin > 0 or spin_polarized):
        middle.append("s_{:d}".format(ispin + 1))
    if iband is not None:
        middle.append("band_{:d}".format(iband + 1))
    middle.append("k_{:d}".format(ikpt + 1))
    return prefix + ".".join(middle) + suffix


def glob_nsbk_files(dir, prefix, suffix, ikpt: int, ispin: int = None, iband: int = None,
                    spin_polarized: bool = False):
    raise NotImplementedError


def __process_single_self_energy_data(fpath):
    fn = os.path.basename(fpath)
    omegas, sigc = _read_aims_single_sigc_dat(fpath)
    n, s, kp, k = fullmatch_nsbk_file_name(fn, r"Sigma\.omega\.", r"\.dat")
    return (n, s, kp, k), omegas, sigc


def read_aims_self_energy_dir(sedir: str = "self_energy",
                              filter_isbk_file: Callable[[int, int, int, int], bool] = None,
                              merge_band_kpoints: bool = False,
                              filethres_mp: int = 10000):
    """read all sigc data in self energy directory `sedir`

    Args:
        sedir (path-like)
        filter_isbk: callable taking 4 int arguments (istate, ispin, iband, ikpt) and returning bool.
            When the int arguments obtained from the file leads to True by calling it, this file will be kept
            in parsing the self-energy. Otherwise the file is filtered out.
        merge_band_kpoints (bool)
        filethres_mp (int): the number of files beyond which multiprocessing will be used.

    Returns:
        1d array: frequencies

        integer: index of the first state

        4d array: sigc data on kgrid, (freq, spin, kpoint, state)

        a list of 4d-arrays: sigc data along band paths, (freq, spin, kpoint, state) each, if merge_band_kpoints False.
        Otherwise a 4d-array, where the third dimension gives the number of all kpoints on band paths
    """
    data_dict_kgrid = {}
    data_dict_band = {}
    omegas = []

    nkpts = 0
    nstates = 0

    fpaths = []
    for fp in os.listdir(sedir):
        matched = fullmatch_nsbk_file_name(os.path.basename(fp), r"Sigma\.omega\.", r"\.dat")
        if matched == []:
            _logger.warn("invalid self energy data file: %s", fp)
            continue
        n, s, kp, k = matched
        if filter_isbk_file is not None and not filter_isbk_file(n, s, kp, k):
            continue
        fpaths.append(fp)

    def set_sigc(n, s, kp, k, sigc):
        if kp is None:
            data_dict_kgrid[(s, k, n)] = sigc
            return
        data_dict_band[(s, kp, k, n)] = sigc

    if len(fpaths) > filethres_mp:
        # TODO: better way to decide max_workers
        with ProcessPoolExecutor(max_workers=1) as executor:
            results = [executor.submit(__process_single_self_energy_data,
                                       os.path.join(sedir, fpath)) for fpath in fpaths]

            for item in as_completed(results):
                (n, s, kp, k), omegas, sigc = item.result()
                set_sigc(n, s, kp, k, sigc)
    else:
        for fp in fpaths:
            (n, s, kp, k), omegas, sigc = __process_single_self_energy_data(os.path.join(sedir, fp))
            set_sigc(n, s, kp, k, sigc)

    # assume all files have the same frequencies (should be the case)
    nomegas = len(omegas)

    kpts_grid = []
    nkpts_grid = 0
    if data_dict_kgrid:
        nspins = max([x for x, _, _ in data_dict_kgrid.keys()]) + 1
        kpts_grid = sorted(set([x for _, x, _ in data_dict_kgrid.keys()]))
        nkpts_grid = len(kpts_grid)
        state_low = min([x for _, _, x in data_dict_kgrid.keys()])
        state_high = max([x for _, _, x in data_dict_kgrid.keys()])
    else:
        nspins = max([x for x, _, _, _ in data_dict_band.keys()]) + 1
        state_low = min([x for _, _, _, x in data_dict_band.keys()])
        state_high = max([x for _, _, _, x in data_dict_band.keys()])

    # not all states are calculated, get it from the indices of lowest and highest state
    nstates = state_high - state_low + 1

    data_kgrid = np.zeros((nomegas, nspins, nkpts_grid, nstates), dtype='complex64')
    if kpts_grid != []:
        for (isp, ik, istate), sigc_freq in data_dict_kgrid.items():
            data_kgrid[:, isp, kpts_grid.index(ik), istate - state_low] = sigc_freq[:]

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

    if merge_band_kpoints:
        if len(data_bands) > 0:
            data_bands = np.concatenate(data_bands, axis=2)
        else:
            data_bands = np.zeros((nomegas, nspins, 0, nstates))

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


def read_aims_self_energy_restart_file(fn: Union[str, os.PathLike] = "self_energy_grid.dat"):
    """Read restart file containing self-energy on imaginary frequency axis"""
    with open(fn, "rb") as h:
        data = h.read()

    header = struct.unpack("i" * 4, data[:16])
    nspin, nkpts, nstates, nfreq = header

    begin, end = 16, 16 + 8 * nfreq
    omega_imag = struct.unpack('d' * nfreq, data[begin:end])
    begin, end = end, 16 + 8 * nfreq + 16 * nfreq * (2 + nspin * nkpts * nstates)
    data = struct.unpack('d' * nspin * nkpts * nstates * nfreq * 2,
                         data[begin:end])
    # convert to numpy array
    omega_imag = np.array(omega_imag)
    data = np.array(data[0::2]) + np.array(data[1::2]) * 1.0j
    data = np.reshape(data, (nspin, nkpts, nstates, nfreq))
    return omega_imag, data
