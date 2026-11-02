# -*- coding: utf-8 -*-
"""GAP commands

Modules heavier than click are imported inside the commands to keep the entry fast.
"""
import sys

import click

from mushroom.cli._utils import Group, check_exclusive, multi_option, opt_casename, opt_dirpath, opt_trans
from typing import Optional

# same as mushroom.gap.Eps.known_kind, which is not imported here to keep the entry fast
_EPS_KINDS = ("eps", "inv", "invm1")


@click.group(cls=Group)
def gap():
    """GAP utilities"""


@gap.command("analyze-eqpev")
@opt_casename
@opt_dirpath
@click.option("-f", "eqpevfile", default=None, help="path of eqpev file")
@opt_trans
@click.option("-g", "method", default="qp",
              type=click.Choice(["g0w0", "gw0", "ks", "hf", "qp"]), help="band structure to analyze")
@click.option("--nohead", "removehead", is_flag=True, help="remove header when display")
@click.option("--occ", "occ_thres", type=float, default=0.01,
              help="occupation threshold passed to Eqpev object")
def analyze_eqpev(casename, dirpath, eqpevfile, trans, method, removehead, occ_thres):
    """analyze GAP eqpeV data from casename.eqpeV_GW and casename.eqpeV_GW0"""
    from mushroom.core.bs import display_band_analysis, display_transition_energies
    from mushroom.core.ioutils import one_line_center_banner
    from mushroom.gap import Eqpev

    if eqpevfile is not None:
        eqpev = Eqpev(peqpev=eqpevfile, dirpath=dirpath, casename=casename, occ_thres=occ_thres)
        if method in ["g0w0", "gw0", "qp"]:
            method = "qp"
        qpbs, qpinfo = eqpev.get_QP_bandstructure, "{} band structure".format(eqpev.method.upper())
        bs, info = {eqpev.method: (qpbs, qpinfo), "qp": (qpbs, qpinfo),
                    "ks": (eqpev.get_KS_bandstructure, "KS band structure"),
                    "hf": (eqpev.get_HF_bandstructure, "HF band structure")}\
            .get(method, (None, None))
    else:
        if method in ["g0w0", "ks", "qp", "hf"]:
            eqpev = Eqpev(dirpath=dirpath, casename=casename, method='g0w0', occ_thres=occ_thres)
            qpbs, qpinfo = eqpev.get_QP_bandstructure, \
                "{} band structure".format(eqpev.method.upper())
            bs, info = {"g0w0": (qpbs, qpinfo), "qp": (qpbs, qpinfo),
                        "ks": (eqpev.get_KS_bandstructure, "KS band structure"),
                        "hf": (eqpev.get_HF_bandstructure, "HF band structure")}\
                .get(method, (None, None))
        else:
            eqpev = Eqpev(dirpath=dirpath, casename=casename, method='gw0', occ_thres=occ_thres)
            bs = eqpev.get_QP_bandstructure
            info = "GW0 band structure"
    if not removehead:
        print(one_line_center_banner(info))
    display_band_analysis(bs(), eqpev.ibzkpts)
    if trans:
        display_transition_energies(trans, bs(), eqpev.ibzkpts)


def _obtain_degw_by_energies(gwe: str, dfte: str, shift: float = 0.0):
    """obtain the self-energy correction from two energy file"""
    import numpy as np

    from mushroom.w2k import read_energy

    gwbs, _, gwkpts, _ = read_energy(gwe)
    dftbs, _, dftkpts, _ = read_energy(dfte)
    if not np.allclose(gwkpts, dftkpts):
        raise ValueError("kpoints in two files are not close to each other. Check the files")
    diff = gwbs - dftbs
    diff.unit = "ev"
    return dftbs + shift, diff.eigen


def _obtain_degw_by_eqpev(peqpev: str, shift: float = 0.0):
    """obtain the self-energy correction from eqpeV file"""
    from mushroom.gap import Eqpev

    eqpev = Eqpev(peqpev)
    return eqpev.get_KS_bandstructure() + shift, eqpev.get_degw(), eqpev.ibandsgw[0] - 1


# pylint: disable=R0914
def _write_degw_data(ene, degw, band_st: int = 0, ap=None, ibands=None, qtl=None, output: Optional[str] = None):
    """write degw data"""
    import numpy as np

    from mushroom.core.data import export_2d_data
    from mushroom.core.dos import split_ap
    from mushroom.core.ioutils import print_file_or_iowrapper

    # NOTE use the first spin channel only
    degw = degw[0, :, :]
    nkpts, nbands = np.shape(degw)
    if ibands is None:
        ibands = list(range(nbands))
    else:
        ibands = [ib - band_st for ib in ibands]
    e = ene.eigen[0, :nkpts, :nbands]
    if ap is None:
        ap = []
    elif qtl is None:
        raise ValueError("qtl must be parsed for atom-projector data")
    ncols = 2 + len(ap)
    with open(output, 'w') as h:
        # write header
        s = ["# " + " ".join(sys.argv),
             "#unit:eV nbands:{:d} nkpts:{:d}".format(nbands, nkpts),
             "#KS degw {}".format(" ".join(ap))]
        print_file_or_iowrapper("\n".join(s), f=h)
        for ib in ibands:
            data = np.zeros((nkpts, ncols))
            data[:, 0] = e[:, ib]
            data[:, 1] = degw[:, ib]
            for ia, _ap in enumerate(ap):
                data[:, 2 + ia] = qtl.get_pwav(*split_ap(_ap))[0, :nkpts, band_st + ib]
            s = ["#Band {}".format(band_st + ib + 1)] + export_2d_data(data)
            print_file_or_iowrapper("\n".join(s), f=h)


@gap.command()
@click.option("--diff", nargs=2, default=None,
              help="path to two energy files for comparison, first for GW and second for DFT")
@click.option("-e", "eqpev", default=None, help="path to eqpeV file")
@click.option("-o", "output", default="degw.dat", help="path to output file")
@click.option("-q", "qtl", default=None, help="path to the qtl file")
@multi_option("-b", "ibands", type=int, metavar="IBAND...", help="index of ibands to dump degw")
@click.option("--shift", type=float, default=0.0,
              help="shift of KS energy in the same unit of file")
@multi_option("--ap", "aps", metavar="AP...", help="atom-projector (ap) string")
@click.pass_context
def degw(ctx, diff, eqpev, output, qtl, ibands, shift, aps):
    """obtain the self-energy correction from GAP2 GW calculation

    It can be achieved either by directly reading eqpeV file, or
    compare two .energy files from GW and DFT calculations.
    """
    from mushroom.w2k import read_qtl

    check_exclusive(ctx, "diff", "eqpev")
    # band_st is the starting index of degw data, used for qtl when eqpeV is parsed
    if diff is not None:
        ene, de = _obtain_degw_by_energies(*diff, shift=shift)
        band_st = 0
    elif eqpev is not None:
        ene, de, band_st = _obtain_degw_by_eqpev(eqpev, shift=shift)
    else:
        raise click.UsageError("please specify either --diff or -e", ctx=ctx)
    ene.unit = "ev"
    bs_qtl = None
    if qtl is not None:
        bs_qtl = read_qtl(qtl)
        bs_qtl.unit = "ev"

    # write data
    _write_degw_data(ene, de, band_st=band_st, ap=list(aps) or None, ibands=list(ibands) or None,
                     qtl=bs_qtl, output=output)


def _plot_eps(eps, iomega: int, compare_eps=None, print_data: bool = False):
    """plot dielectric matrix"""
    import matplotlib.pyplot as plt
    import numpy as np

    fig, ax = plt.subplots()
    realpart = eps.get_eps(iomega).real
    if compare_eps is not None:
        realpart = eps.get_eps(iomega).real - compare_eps.get_eps(iomega).real
    vmax = np.max(np.absolute(realpart))
    vmin = 1.0
    cmap = "GnBu"
    if print_data:
        print(realpart)
    if compare_eps is not None:
        vmin = -vmax
        cmap = "RdBu"
    # eps usually converges to 1
    c = ax.pcolor(realpart, cmap=cmap, vmin=vmin, vmax=vmax)
    fig.colorbar(c, ax=ax)
    return fig, ax


def _print_eps_omega(eps, iomega):
    """print out dielectric matrix at a particular frequency"""
    epsdata = eps.get_eps(iomega)
    print("Is epsilon(iomega={:d}) Hermitian? {}".format(iomega, eps.is_hermitian(iomega)))
    print("                  long-wavelength? {}".format(eps.is_q0))
    s = "epshead"
    if eps.is_q0:
        s = "E_macro"
    print("{} (NLF) = {}".format(s, epsdata[0, 0]))
    epsdata = eps.get(iomega)
    # if the raw data is related to the inverse, print emac data with local field
    if eps.kind == "invm1":
        print("         (LF) = {}".format(1.0 / (epsdata[0, 0] + 1.0)))
    elif eps.kind == "inv":
        print("         (LF) = {}".format(1.0 / epsdata[0, 0]))


@gap.command("eps")
@click.argument("epsfile")
@click.option("-t", "kind", type=click.Choice(_EPS_KINDS), default="invm1", help="kind of eps file")
@click.option("-n", "nbyte_recl", type=int, default=1, help="bytes unit of record length")
@click.option("-w", "iomega", type=int, default=None,
              help="index of frequency point (start from 0), required by --plot")
@click.option("--plot", is_flag=True, help="plot the dielectric matrix")
@click.option("--show", is_flag=True, help="show the dielectric matrix plot")
@click.option("--data", is_flag=True, help="print the realpart of dielectric matrix elements")
@click.option("--diff", "compare_eps", default=None, help="path to eps file for comparison")
@click.pass_context
def eps_(ctx, epsfile, kind, nbyte_recl, iomega, plot, show, data, compare_eps):
    """read and plot the dielectric matrix"""
    import matplotlib.pyplot as plt

    from mushroom.core.display import set_np_linewidth_ratio
    from mushroom.gap import Eps
    from mushroom.visual.pyplot import rc_gracify

    if plot and iomega is None:
        raise click.UsageError("-w is required by --plot", ctx=ctx)
    # make grace style as default
    rc_gracify()
    # add numpy array print for large terminal
    set_np_linewidth_ratio(ratio=0.75, thres=100)

    iq = int(epsfile.split('q')[-1])
    eps = Eps(epsfile, is_q0=iq == 1, kind=kind, nbyte_recl=nbyte_recl, cache=True)
    if iomega is not None:
        _print_eps_omega(eps, iomega)
        if plot or show:
            if compare_eps is not None:
                compare_eps = Eps(compare_eps, is_q0=iq == 1, kind=kind, nbyte_recl=nbyte_recl,
                                  cache=True)
            fig, _ = _plot_eps(eps, iomega, compare_eps=compare_eps, print_data=data)
            if show:
                plt.show()
            fig.savefig("eps_iq_{}_iomega_{}.png".format(iq, iomega))
    else:
        for i in range(eps.nomega):
            _print_eps_omega(eps, i)


def _plot_vmat(vmat, compare_vmat=None, maxsize: Optional[int] = None, center_zero: bool = False):
    """plot Coulomb matrix"""
    import matplotlib.pyplot as plt
    import numpy as np

    fig, ax = plt.subplots()
    realpart = vmat.vmat.real
    if compare_vmat is not None:
        realpart = vmat.vmat.real - compare_vmat.vmat.real
    if maxsize:
        if maxsize > 0:
            realpart = realpart[:maxsize, :maxsize]
        elif maxsize < 0:
            realpart = realpart[maxsize:, maxsize:]
    if center_zero:
        vmax = np.max(np.absolute(realpart))
        c = ax.pcolor(realpart, cmap="RdBu", vmin=-vmax, vmax=vmax)
    else:
        c = ax.pcolor(realpart, cmap="RdBu")
    fig.colorbar(c, ax=ax)
    return fig, ax


def _plot_negative_eigvec(vmat):
    """plot the first eigenvector of Coulomb matrix when its eigenvalue is negative"""
    import matplotlib.pyplot as plt
    import numpy as np

    fig, ax = plt.subplots()
    evec = vmat.evec
    ev = vmat.eval
    ax.set_xlim([1, vmat.msize])
    if ev[0] < 0:
        comps = np.absolute(evec[:, 0])
        maxcomp = np.max(comps)
        imaxcomp = np.argmax(comps) + 1
        ax.bar(list(range(1, vmat.msize + 1)), comps)
        ax.annotate("Largest comp.: {:5.3f} ({:d} of {:d})".format(maxcomp, imaxcomp, vmat.msize),
                    (0.05, 0.95), xycoords="axes fraction")
    return fig, ax


@gap.command("vmat")
@click.argument("vmatfile")
@click.option("-n", "nbyte_recl", type=int, default=1,
              help="unit of record length. Usually 1/4 for gfortran/intel")
@click.option("-s", "maxsize", type=int, default=None, help="max size of the matrix element to show")
@click.option("--plot", is_flag=True, help="save the v-matrix plot")
@click.option("--show", is_flag=True, help="show the v-matrix plot")
@click.option("--diff", default=None, help="path of vmat file to compare when plot")
@click.option("--nd", "nbyte_recl_diff", type=int, default=None,
              help="unit of record length of compare vmat")
@click.option("--cz", "center_zero", is_flag=True, help="center the color map at zero")
@click.option("-D", "debug", is_flag=True, help="debug mode")
def vmat_(vmatfile, nbyte_recl, maxsize, plot, show, diff, nbyte_recl_diff, center_zero, debug):
    """plot Coulomb matrix"""
    import matplotlib.pyplot as plt

    from mushroom.core.display import set_np_linewidth_ratio
    from mushroom.gap import Vmat
    from mushroom.visual.pyplot import rc_gracify

    # make grace style as default
    rc_gracify()
    # add numpy array print for large terminal
    set_np_linewidth_ratio(ratio=0.75, thres=100)

    vmat = Vmat(vmatfile, nbyte_recl=nbyte_recl)
    if debug:
        print("=Debug=: read record length and unit: {}, {}".format(vmat.recl, vmat.nbyte_recl))
    print("     matrix size =", vmat.msize)
    print("Is vmat Hermitian?", vmat.is_hermitian())
    print("diagonal elements:")
    print(vmat.diag)
    print("      eigenvalues:")
    print(vmat.eval)
    if plot or show:
        compare_vmat = None
        if diff is not None:
            if nbyte_recl_diff is None:
                nbyte_recl_diff = nbyte_recl
            compare_vmat = Vmat(diff, nbyte_recl=nbyte_recl_diff)
        fig, _ = _plot_vmat(vmat, compare_vmat=compare_vmat, maxsize=maxsize,
                            center_zero=center_zero)
        if show:
            plt.show()
        if diff:
            fig.savefig("diff_vmat.png")
        else:
            fig.savefig("vmat.png")
        fig, _ = _plot_negative_eigvec(vmat)
        fig.savefig("first_nega_eigvec.png")
