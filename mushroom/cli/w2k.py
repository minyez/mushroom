# -*- coding: utf-8 -*-
"""WIEN2k commands

Modules heavier than click are imported inside the commands to keep the entry fast.
"""
import click

from mushroom.cli._utils import (Group, check_exclusive, get_ksymbols, multi_option, opt_casename,
                                 opt_dirpath, opt_fig_ext, opt_ksymbols, opt_removek, opt_trans)

_opt_energyfile = click.option("-f", "energyfile", default=None, help="path of energy file")


@click.group(cls=Group)
def w2k():
    """WIEN2k utilities"""


# pylint: disable=R0914
def _get_bs_kpath(casename, dirpath, energyfile, efermi, unify_x=False):
    """return BandStructure and KPathLinearizer objects"""
    from mushroom.core.ioutils import greeks
    from mushroom.core.kpoints import KPathLinearizer
    from mushroom.w2k import Struct, get_inputs, read_energy

    pstruct, penergy, _ = get_inputs("struct", "energy", "in1", casename=casename,
                                     dirpath=dirpath, relative="CWD")
    if energyfile is not None:
        penergy = energyfile
    struct = Struct.read(pstruct)
    cell = struct.get_cell()
    # set to angstrom unit for standard and possible comparison with VASP/GPAW/abinit results
    cell.unit = "ang"
    bs, _, kpts, symbols = read_energy(penergy, efermi=efermi)
    kp = KPathLinearizer(kpts, recp_latt=cell.b, unify_x=unify_x)
    # convert greek letters to latex for grace encoding
    ksymbols = []
    if symbols:
        for _, s in symbols:
            sc = s.capitalize()
            if sc in greeks:
                ksymbols.append("\\" + sc)
            else:
                ksymbols.append(sc)
    return bs, kp, [x[:2].strip() for x in struct.atms_types], ksymbols


def _plot_pwav(graph, x, bs, apbs, spin, ref, scale, colors=None, prop_area=False):
    """plot partial waves

    Args:
        graph (Graph)
        x (1d array)
        bs (BandStructure)
        spin (int)
        scale (float)
        colors (list)
        prop_area (bool)
    """
    import numpy as np

    from mushroom.core.bs import split_apb
    from mushroom.visual.graceplot import prefer_gracecolors

    if colors is None:
        colors = prefer_gracecolors
    for i, apb in enumerate(apbs):
        atms, prjs, bands = split_apb(apb)
        pwav = bs.get_pwav(atms, prjs, bands)[spin, :, :]
        eigen = bs.get_eigen(bands)[spin, :, :] - ref
        kwargs = {
            "datatype": "xysize",
            "color": colors[i % len(colors)],
            "label": "-".join(str(x) for x in apb.split(":")[:2]),
            "ls": "none",
        }
        if prop_area:
            graph.plot(x, eigen.transpose(), size=np.sqrt(pwav.transpose()) * scale, **kwargs)
        else:
            graph.plot(x, eigen.transpose(), size=pwav.transpose() * scale, **kwargs)


@w2k.command()
@opt_casename
@opt_dirpath
@_opt_energyfile
@opt_ksymbols
@click.option("-o", "output", default="plotband.agr", help="path of agr file to export")
@opt_removek
@opt_fig_ext
@click.option("--ef", "efermi", type=float, default=None, help="Fermi energy")
@click.option("-s", "scale", type=float, default=1.0, help="scale for the area of partial wave")
@click.option("--unifyx", is_flag=True, help="unify abscissa (x)")
@click.option("--area", "prop_area", is_flag=True,
              help="area proportional to partial wave instead of diameter")
@click.option("--vbmz", "vbm_zero", is_flag=True, help="use VBM as energy zero")
@click.option("--ferz", "fermi_zero", is_flag=True, help="use Fermi energy as energy zero")
@click.option("--spin", type=click.IntRange(0, 1), default=0, help="spin to draw")
@click.option("-e", "energy_range", default=None, help="energy range, e.g. 'm8~5' for -8.0 to 5.0")
@click.option("-q", "qtl", default=None, help="path to the qtl file")
@multi_option("--apb", "apbs", metavar="APB...",
              help="atom-projector-band (apb) string, separated by whitespace")
@click.pass_context
def band(ctx, casename, dirpath, energyfile, ksymbols, output, removek, fig_ext, efermi, scale,
         unifyx, prop_area, vbm_zero, fermi_zero, spin, energy_range, qtl, apbs):
    """draw band from wien2k output and export to a grace file"""
    from mushroom.core.ioutils import decode_float_ends, get_filename_wo_ext
    from mushroom.visual.graceplot import Plot
    from mushroom.w2k import read_qtl

    check_exclusive(ctx, "vbm_zero", "fermi_zero")

    bs, kp, atms, symbols = _get_bs_kpath(casename, dirpath, energyfile, efermi, unify_x=unifyx)
    if qtl is not None:
        pwav, prjs = read_qtl(qtl, data_only=True)
        bs.parse_proj(pwav, atms, prjs)
    p, ax = Plot.subplots()
    bs.unit = "ev"
    ref = 0.0
    if fermi_zero:
        ref = bs.efermi
    if vbm_zero:
        ref = bs.vbm
    ax.plot(kp.x, bs.eigen[0, :, :].transpose() - ref, color="k", symbol="none")
    ax.x.set_major(grid=True, color="grey", lw=3, ls="dashed")
    # try to use symbols found in the energy file if not specified
    ax.x.set_spec(kp.special_x, labels=get_ksymbols(ksymbols) if ksymbols else symbols)
    ax.set_xlim(0.0, kp.x[-1] + 0.0001)
    scale_plot = (kp.x[-1] - kp.x[0]) / len(kp.x) * 36.0 * scale
    if apbs:
        _plot_pwav(ax, kp.x, bs, apbs, spin, ref, scale_plot, prop_area=prop_area)

    if energy_range is not None:
        try:
            emin, emax = decode_float_ends(energy_range)
            ax.set_ylim(ymin=emin, ymax=emax)
            ax.tight_graph(xscale=None, yscale=None)
        except ValueError as err:
            raise ValueError("invalid energy range", energy_range) from err
    else:
        ax.tight_graph(xscale=None)

    ax.y.set_label("Energy (eV)")
    # draw zero line for Fermi level
    ax.axhline(0.0, ls="dashed", lw=2)
    p.write(file=output)
    if fig_ext is not None:
        p.savefig(get_filename_wo_ext(output) + "." + fig_ext)


def _plot_pdos(graph, dos, aps, spin=None, colors=None):
    """plot projected density of states and export to pdos.dat

    Args:
        graph (Graph)
        dos (DensityOfStates)
        aps (str) : atom-projector
    """
    from mushroom.core.data import export_2d_data
    from mushroom.core.dos import split_ap
    from mushroom.visual.graceplot import prefer_gracecolors

    if colors is None:
        colors = prefer_gracecolors
    with open('pdos.dat', 'w') as pdos_dat:
        egrid = dos.egrid
        for i, ap in enumerate(aps):
            atms, prjs = split_ap(ap)
            pdos = dos.get_pdos(ispin=spin, atm=atms, prj=prjs)
            graph.plot(egrid - dos.efermi, pdos, color=colors[i % len(colors)], symbol="none",
                       label="-".join(str(x) for x in ap.split(":")))
            print("#atom-projector:{}".format(ap), file=pdos_dat)
            print("\n".join(export_2d_data([egrid, pdos], transpose=True)),
                  file=pdos_dat, end="\n\n")


@w2k.command("dos")
@opt_casename
@click.option("-u", "unit", default=None,
              help="unit of dos input, default to detect by the extension")
@multi_option("-d", "dosfiles", metavar="FILE...", required=True, help="path of dosev files")
@opt_dirpath
@click.option("-o", "output", default="plotpdos.agr",
              help="path of agr file to export projected density of states")
@click.option("-e", "energy_range", default=None, help="energy range, e.g. 'm8~5' for -8.0 to 5.0")
@multi_option("--ap", "aps", metavar="AP...", help="atom-projector (ap) string")
@opt_fig_ext
def dos_(casename, unit, dosfiles, dirpath, output, energy_range, aps, fig_ext):
    """draw total and projected density of states (DOS) from wien2k output"""
    from mushroom.core.ioutils import decode_float_ends, get_filename_wo_ext
    from mushroom.core.logger import create_logger
    from mushroom.visual.graceplot import Plot
    from mushroom.w2k import Struct, get_inputs, read_dos

    _logger = create_logger("w2k_dos")

    pstruct = get_inputs("struct", casename=casename, dirpath=dirpath, relative="CWD")[0]
    struct = Struct.read(pstruct)
    _logger.info("reading dos from atms: %r", dosfiles)
    dos = read_dos(*dosfiles, unit=unit, mults=struct.mults)
    # plot to ev unit
    dos.unit = "ev"

    p, ax = Plot.subplots()
    ax.plot(dos.egrid - dos.efermi, dos.get_tdos(ispin=-1), color="k", symbol="none", label="Total")
    if energy_range is not None:
        try:
            emin, emax = decode_float_ends(energy_range)
            ax.set_xlim(xmin=emin, xmax=emax)
            ax.tight_graph(yscale=1.1, xscale=None)
        except ValueError as err:
            raise ValueError("invalid energy range", energy_range) from err
    else:
        ax.tight_graph(yscale=1.1)

    ax.set_ylim(ymin=0.0)
    ax.set_legend(loc="upper left")
    ax.x.set_label("Energy ({})".format(dos.unit))
    ax.y.set_label("Density of states (arb. units)", charsize=2.)
    ax.y.set_ticklabel(switch="off")
    ax.axvline(0.0, ls="dashed", lw=3, color="grey")

    if aps:
        dos.atms = [x[:2].strip() for x in struct.atms_types]
        _logger.info("available atms: %r", dos.atms)
        _logger.info("available prjs: %r", dos.prjs)
        _plot_pdos(ax, dos, aps)

    p.write(file=output)
    if fig_ext is not None:
        p.savefig(get_filename_wo_ext(output) + "." + fig_ext)


@w2k.command()
@opt_casename
@opt_dirpath
@_opt_energyfile
@click.option("-u", "unit", default="eV", type=click.Choice(["eV", "au", "ry", "ha"]),
              help="unit of energy")
@opt_trans
@click.option("--ef", "efermi", type=float, default=None, help="fermi energy in Ry")
@opt_removek
@click.option("-D", "debug", is_flag=True, help="debug mode")
def gap(casename, dirpath, energyfile, unit, trans, efermi, removek, debug):
    """obtain band gap from WIEN2k energy file"""
    from mushroom.core.bs import display_band_analysis, display_transition_energies
    from mushroom.w2k import get_inputs, read_energy

    penergy = get_inputs("energy", casename=casename, dirpath=dirpath, relative="CWD")[0]
    if energyfile is not None:
        penergy = energyfile
    bs, _, kpts, _ = read_energy(penergy, efermi=efermi)
    if debug:
        print(bs.occ)
        print(bs.ivbm, bs.icbm)
        print(kpts)
    display_band_analysis(bs, kpts, unit=unit)
    if trans:
        display_transition_energies(trans, bs, kpts, unit)
