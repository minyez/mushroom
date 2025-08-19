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
    output_have_occ = True
    success_run = False

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
        if l.strip().lower().startswith("librpa finished"):
            success_run = True
    if not success_run:
        _logger.warning("%s did not finish successfully")

    if len(i_qpe_headlines) == 0:
        raise ValueError("QP energies results are not available from output: %r" % fn)

    # prune previous lines
    i_qpe_headlines = np.array(i_qpe_headlines)
    lines = lines[i_qpe_headlines[0]:]
    i_qpe_headlines -= i_qpe_headlines[0]

    # check if occ is included in the output, by checking the header line
    try:
        lines[i_qpe_headlines[0] + 2].index("occ")
    except ValueError:
        output_have_occ = False

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
    if output_have_occ:
        occ, eks, vxc, vex, eqp = np.loadtxt(StringIO("".join(qpe_lines)), usecols=[1, 2, 3, 4, -1], unpack=True)
        occ = np.reshape(occ, (nspins, nkpts, nstates))
    else:
        eks, vxc, vex, eqp = np.loadtxt(StringIO("".join(qpe_lines)), usecols=[1, 2, 3, -1], unpack=True)
        occ = None
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


def get_occ_numbers_from_bandout(fn_bandout: str = "band_out"):
    """"""
    with open(fn_bandout, 'r') as h:
        lines = h.readlines()
    n_spins = int(lines[1].split()[-1])
    n_kpts = int(lines[0].split()[-1])
    n_states = int(lines[2].split()[-1])
    occ = []
    for i in range(n_kpts * n_spins):
        occ.extend(
            float(x.split()[1]) for x in lines[6 + (n_states + 1) * i:6 +
                                               (n_states + 1) * i + n_states])
    occ = np.array(occ).reshape(n_spins, n_kpts, n_states)
    return occ


def read_librpa_dimension(fn: Union[str, os.PathLike] = "librpa.out"):
    with open(fn, 'r') as h:
        lines = h.readlines()
    # Read all internal parameters
    keys = [
        "n_procs",
        "n_threads",
        "n_atoms",
        "n_freq",
        "n_spin",
        "n_kpts",
        "n_bands",
        "n_basis",
    ]

    d = {}
    for l in lines:
        if l.startswith("Maximumal number of threads"):
            d["n_threads"] = int(l.split()[-1])
            _logger.info("Found dimension n_threads: %d", d["n_threads"])
        if l.startswith("Total number of tasks:"):
            d["n_procs"] = int(l.split()[-1])
            _logger.info("Found dimension n_procs: %d", d["n_procs"])
        if l.startswith("| Number of atoms"):
            d["n_atoms"] = int(l.split()[-1])
            _logger.info("Found dimension n_atoms: %d", d["n_atoms"])
        if l.startswith("nfreq = "):
            d["n_freq"] = int(l.split()[-1])
            _logger.info("Found dimension n_freq: %d", d["n_freq"])
        if l.startswith("| number of spins"):
            d["n_spin"] = int(l.split()[-1])
            _logger.info("Found dimension n_spin: %d", d["n_spin"])
        if l.startswith("| number of k-points"):
            d["n_kpts"] = int(l.split()[-1])
            _logger.info("Found dimension n_kpts: %d", d["n_kpts"])
        if l.startswith("| number of bands"):
            d["n_bands"] = int(l.split()[-1])
            _logger.info("Found dimension n_bands: %d", d["n_bands"])
        if l.startswith("| number of NAOs"):
            d["n_basis"] = int(l.split()[-1])
            _logger.info("Found dimension n_basis: %d", d["n_basis"])

    float_pars = [
        "libri_chi0_threshold_C",
        "libri_chi0_threshold_G",
        "libri_exx_threshold_C",
        "libri_exx_threshold_D",
        "libri_exx_threshold_V",
        "libri_g0w0_threshold_C",
        "libri_g0w0_threshold_G",
        "libri_g0w0_threshold_Wc",
    ]

    try:
        beg = "===== Begin control parameters =====\n"
        lines_control_pars = lines[lines.index(beg) + 1:]
        end = "===== End control parameters   =====\n"
        lines_control_pars = lines_control_pars[:lines_control_pars.index(end)]
    except ValueError:
        pass

    for l in lines_control_pars:
        k, _, v = l.split()
        if k in float_pars:
            v = float(v)
        d[k] = v

    return d


def _check_librpa_finished(lines) -> bool:
    for l in reversed(lines):
        if l.strip().lower().startswith("librpa finished"):
            return True
    return False


def read_librpa_timing(fn: Union[str, os.PathLike] = "librpa.out", details: bool = False):
    """Read timing data of LibRPA from output file

    Returns:
        dict, if the calculation finished successfully.
        Otherwise None.
    """
    # Load timing lines
    with open(fn, 'r') as h:
        lines = h.readlines()
    for i, l in enumerate(lines):
        if l.startswith("Total   "):
            break
    lines = [x.rstrip() for x in lines[i:]]

    # check if finished
    finished = _check_librpa_finished(lines)
    if not finished:
        return None

    # all useful entries
    scan = {
        "total": ("Total   ", ),
        "cal_chi0s": ("Call cal_chi0s", ),
        "cal_exx": ("Call libRI Hexx calculation", ),
        "cal_sigc": ("Call libRI cal_Sigc", ),
        "chi0s_total": ("Build response function chi0", ),
        "sigc_total": ("Build correlation self-energy",
                       "Build real-space correlation self-energy"),
        "wc_from_chi0_total": ("Build screened interaction", ),
        "exx_total": ("Build exchange self-energy", ),
        "load_coul_cut": ("Load truncated Coulomb", ),
        "wc_2d_ij": ("Convert Wc, 2D -> IJ", ),
        "wc_qw_rt": ("Tranform Wc (q,w) -> (R,t)", ),
        "g0w0_total": ("G0W0 quasi-particle", ),
        "se_export": ("Export self-energy in KS basis", ),
        # some detailed timing
        "chi0_loop_ri": ("Loop over LibRI", ),
        "build_gf_Rt_libri": ("build_gf_Rt_libri", ),
        "collect_chi_R_blocks": ("Collect all R blocks", ),
        "chi0_ft_ct": ("Fourier and Cosine transform", ),
        "prepare_sqrt_v_cut": ("Prepare sqrt of truncated Coulomb", ),
        "prepare_sqrt_v": ("Prepare sqrt of bare Coulomb", ),
        "chi0_2d_block": ("Prepare Chi0 2D block", ),
        "polarizability": ("Compute dielectric matrix", ),
        "invert_dielmat": ("Invert dielectric matrix", ),
        "build_wc_from_invdm": ("Multiply truncated Coulomb", ),
        "sigc_setup_libri_c": ("Setup LibRI C data", ),
        "compute_gf_sigc": ("Compute G(R,t) and G(R,-t)", ),
        "sigc_ctst": ("Transform Sigc (R,t) -> (R,w)", ),
    }
    entry_timing = {}

    # Analyse lines. Need to handle different versions
    for key, entries in scan.items():
        for entry in entries:
            # print(entry)
            for l in lines:
                if l.strip().startswith(entry):
                    _logger.debug("found entry %s for key %s", entry, key)
                    level = l.find(entry) // 2
                    words = l.split()
                    ncalls = int(words[-3])
                    cput = float(words[-2])
                    wallt = float(words[-1])
                    entry_timing[key] = [level, ncalls, cput, wallt]
        if key not in entry_timing:
            entry_timing[key] = [-1, 0, 0, 0]

    # Timing needs extra handling
    # 1. Exclude time of reading cut Coulomb from G0W0 total, due to different versions
    load_coul_cut = entry_timing["load_coul_cut"]
    g0w0_total = entry_timing["g0w0_total"]
    if load_coul_cut is not None and g0w0_total is not None:
        # print(load_coul_cut, g0w0_total)
        if load_coul_cut[0] != g0w0_total[0]:
            g0w0_total[2] -= load_coul_cut[2]
            g0w0_total[3] -= load_coul_cut[3]
    # 2. Exclude writing self-energy file time
    if entry_timing["se_export"] is not None and g0w0_total is not None:
        g0w0_total[2] -= entry_timing["se_export"][2]
        g0w0_total[3] -= entry_timing["se_export"][3]

    entries_normal = [
        "total", "cal_chi0s", "cal_exx", "cal_sigc",
        "g0w0_total", "chi0s_total", "exx_total", "sigc_total", "wc_from_chi0_total",
        "wc_2d_ij", "wc_qw_rt",
    ]
    entries_details = list(scan.keys())

    # Summary directory
    d = {}
    if details:
        for key in entries_normal:
            d[key] = entry_timing[key]
    else:
        for key in entries_details:
            d[key] = entry_timing[key]

    return d
