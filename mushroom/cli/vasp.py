# -*- coding: utf-8 -*-
"""VASP commands

Modules heavier than click are imported inside the commands to keep the entry fast.
"""
import sys

import click

from mushroom.cli._utils import (Group, check_exclusive, get_ksymbols, multi_option, opt_fig_ext,
                                 opt_ksymbols, opt_removek, opt_trans, optional_value_option)

_opt_poscar = click.option("--pos", "poscar", default="POSCAR", help="POSCAR structure file")


@click.group(cls=Group)
def vasp():
    """VASP utilities"""


@vasp.command()
@click.option("-v", "eigenval", default="EIGENVAL", help="EIGENVAL file to read band data")
@_opt_poscar
@click.option("-o", "output", default="plotband.agr", help="path of agr file to export")
@click.option("--data", "data_only", is_flag=True, help="only extract and print data, do not plot")
@opt_removek
@opt_fig_ext
@click.option("-e", "energy_range", default=None,
              help="energy range (y-axis), e.g. 'm8~5' for -8.0 to 5.0")
@click.option("--ferz", "fermi_zero", is_flag=True, help="use Fermi energy as energy zero")
@click.option("--vbmz", "vbm_zero", is_flag=True, help="use VBM as energy zero")
@opt_ksymbols
@optional_value_option("--sym-kf", "ksymbols_kf", const="KPOINTS", default=None,
                       help="Read symbols of high symmetry points from KPOINTS file")
@click.pass_context
def band(ctx, eigenval, poscar, output, data_only, removek, fig_ext, energy_range,
         fermi_zero, vbm_zero, ksymbols, ksymbols_kf):
    """draw band structure from vasp output and export to an XmGrace plot."""
    from mushroom.core.bs import display_band_analysis
    from mushroom.core.cell import Cell
    from mushroom.core.ioutils import decode_float_ends, get_filename_wo_ext
    from mushroom.core.kpoints import KPathLinearizer
    from mushroom.vasp import read_eigen
    from mushroom.visual.graceplot import Plot

    check_exclusive(ctx, "fermi_zero", "vbm_zero")
    check_exclusive(ctx, "ksymbols", "ksymbols_kf")

    p, ax = Plot.subplots(1, 1, background=False)
    c = Cell.read(poscar)

    # get band energies from EIGENVAL
    bs, _, kpts = read_eigen(eigenval, filter_k_before=removek)
    display_band_analysis(bs, kpts)
    if data_only:
        return
    ref = 0.0
    if vbm_zero:
        ref = bs.vbm
    if fermi_zero:
        ref = bs.efermi
    kp = KPathLinearizer(kpts, c.b)
    ax.plot(kp.x, bs.eigen[0, :, :].transpose() - ref, color="k", symbol="none")
    ax.x.set_major(grid=True, color="grey", lw=3, ls="dashed")
    ax.x.set_spec(kp.special_x, labels=get_ksymbols(ksymbols))
    if energy_range is not None:
        try:
            emin, emax = decode_float_ends(energy_range)
            ax.set_ylim(ymin=emin, ymax=emax)
        except ValueError as err:
            raise ValueError("invalid energy range", energy_range) from err
    ax.set_xlim(0.0, kp.x[-1] + 0.0001)
    ax.set_ylim(-6, 6)
    ax.y.set_major(major=4)
    ax.y.set_label("Energy (eV)")
    # draw zero line
    ax.axhline(0.0, ls="dashed")
    p.write(file=output)
    if fig_ext is not None:
        p.savefig(get_filename_wo_ext(output) + "." + fig_ext)


@vasp.command()
@click.option("-f", "pchg", default="CHGCAR", help="path to the CHGCAR file")
def chg(pchg):
    """analyse VASP CHG/CHGCAR file

    The command will do the following:

    \b
        - write a cube file for visualization (.cube file in the same path)

    If VESTA is used to visualize, the cube is unnecessary as
    CHGCAR file can be directly read and the periodicity is correctly handled.
    """
    from mushroom.vasp import read_chg

    density = read_chg(pchg)
    with open(pchg + ".cube", 'w') as h:
        print(density.export_cube(), file=h)


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
        print("#fermi-energy: {}".format(dos.efermi), file=pdos_dat)
        egrid = dos.egrid
        for i, ap in enumerate(aps):
            atms, prjs = split_ap(ap)
            pdos = dos.get_pdos(ispin=spin, atm=atms, prj=prjs)
            graph.plot(egrid - dos.efermi, pdos, color=colors[i % len(colors)], symbol="none",
                       label="-".join(str(x) for x in ap.split(":")))
            print("#atom-projector:{}".format(ap), file=pdos_dat)
            print("\n".join(export_2d_data([egrid, pdos], transpose=True)),
                  file=pdos_dat, end="\n\n")


def _plot_tdos(graph, dos):
    """plot total density of states and export to tdos.dat"""
    from mushroom.core.data import export_2d_data

    graph.plot(dos.egrid - dos.efermi, dos.get_tdos(ispin=-1), color="k", symbol="none", label="Total")
    with open('tdos.dat', 'w') as tdos_dat:
        print("#fermi-energy: {}".format(dos.efermi), file=tdos_dat)
        print("\n".join(export_2d_data([dos.egrid, dos.get_tdos(ispin=-1)], transpose=True)),
              file=tdos_dat)


@vasp.command("dos")
@click.option("-d", "doscar", default="DOSCAR", help="DOSCAR file to read")
@click.option("-x", "vasprunxml", default=None, help="vasprun.xml file")
@click.option("-o", "output", default="plotpdos.agr",
              help="path of agr file to export projected density of states")
@click.option("--pos", "poscar", default="POSCAR", help="POSCAR structure file to read atoms")
@click.option("-e", "energy_range", default=None, help="energy range, e.g. 'm8~5' for -8.0 to 5.0")
@multi_option("--ap", "aps", metavar="AP...", help="atom-projector (ap) string")
@opt_fig_ext
@click.pass_context
def dos_(ctx, doscar, vasprunxml, output, poscar, energy_range, aps, fig_ext):
    """draw projected density of states from vasp output DOSCAR and export to an XmGrace plot.

    Plot is already shifted such that Fermi-energy is zero.
    Exported data is not shifted.
    """
    from mushroom.core.cell import Cell
    from mushroom.core.ioutils import decode_float_ends, get_filename_wo_ext
    from mushroom.vasp import read_doscar
    from mushroom.visual.graceplot import Plot

    check_exclusive(ctx, "doscar", "vasprunxml")

    read_pdos = len(aps) > 0
    if vasprunxml is None:
        dos = read_doscar(doscar, read_pdos=read_pdos)
    else:
        raise NotImplementedError
    p, ax = Plot.subplots()
    _plot_tdos(ax, dos)
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

    if read_pdos:
        c = Cell.read(poscar)
        dos.atms = c.atms
        _plot_pdos(ax, dos, aps)

    p.write(file=output)
    if fig_ext is not None:
        p.savefig(get_filename_wo_ext(output) + "." + fig_ext)


@vasp.command()
@click.option("-v", "eigenval", default="EIGENVAL", help="EIGENVAL file to read band data")
@opt_removek
@opt_trans
@click.option("-D", "debug", is_flag=True, help="debug mode")
def gap(eigenval, removek, trans, debug):
    """compute the band gap from vasp output"""
    from mushroom.core.bs import display_band_analysis, display_transition_energies
    from mushroom.vasp import read_eigen

    bs, _, kpts = read_eigen(eigenval, filter_k_before=removek)
    display_band_analysis(bs, kpts)
    if trans:
        display_transition_energies(trans, bs, kpts)


# pylint: disable=R0914
def _plot_pwav(graph, x, bs, apbs, spin, scale, colors=None, prop_area=False):
    """plot partial waves and export to pwav.dat

    Args:
        graph (Graph)
        x (1d array)
        bs (BandStructure)
        apbs (list)
        spin (int)
        scale (float)
        colors (list)
        prop_area (bool)
    """
    import numpy as np

    from mushroom.core.bs import split_apb
    from mushroom.core.data import export_2d_data
    from mushroom.visual.graceplot import prefer_gracecolors

    if colors is None:
        colors = prefer_gracecolors
    with open('pwav.dat', 'w') as pwav_dat:
        for i, apb in enumerate(apbs):
            atms, prjs, bands = split_apb(apb)
            pwav = bs.get_pwav(atms, prjs, bands)[spin, :, :]
            eigen = bs.get_eigen(bands)[spin, :, :] - bs.efermi
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
            print("#atom-projector-band:{}".format(apb), file=pwav_dat)
            print("\n".join(export_2d_data(pwav)), file=pwav_dat, end="\n\n")


@vasp.command()
@click.option("-p", "procar", default="PROCAR", help="PROCAR file to read band data")
@_opt_poscar
@opt_ksymbols
@click.option("-o", "output", default="plotpwav.agr", help="path of agr file to export")
@opt_removek
@click.option("--area", "prop_area", is_flag=True,
              help="area proportional to partial wave instead of diameter")
@multi_option("--apb", "apbs", metavar="APB...", help="atom-projector-band (apb) string")
@click.option("-s", "scale", type=float, default=1.0, help="scale for the area of partial wave")
@click.option("--spin", type=click.IntRange(0, 1), default=0, help="spin to draw")
@opt_fig_ext
@click.option("-e", "energy_range", default=None, help="energy range, e.g. 'm8~5' for -8.0 to 5.0")
def pwav(procar, poscar, ksymbols, output, removek, prop_area, apbs, scale, spin, fig_ext,
         energy_range):
    """draw projected band structure (or partial wave) from vasp output and export to an XmGrace plot.

    In the plot, the value of partial wave is proportional to the diameter of the circle.
    The summed partial wave for atom and projector is stored in ``pwav.dat``

    For atom-projector-band (apb) string, see ``mushroom.core.bs.split_apb``
    """
    from mushroom.core.cell import Cell
    from mushroom.core.ioutils import decode_float_ends, get_filename_wo_ext
    from mushroom.core.kpoints import KPathLinearizer
    from mushroom.core.logger import create_logger
    from mushroom.vasp import read_procar
    from mushroom.visual.graceplot import Plot

    _logger = create_logger("mv_pwav")

    c = Cell.read(poscar)
    bs, kpts = read_procar(procar, filter_k_before=removek)
    bs.atms = c.atms
    kp = KPathLinearizer(kpts, c.b)
    if spin >= bs.nspins:
        raise ValueError("ispin {} >= nspins = {}".format(spin, bs.nspins))
    p, ax = Plot.subplots(1, 1, description=" ".join(sys.argv))
    ax.set_xlim(0.0, kp.x[-1] + 0.001)
    # draw bands
    ax.plot(kp.x, bs.eigen[spin, :, :].transpose() - bs.efermi, color="k", symbol="none")
    ax.x.set_major(grid=True, color="grey", lw=3, ls="dashed")
    ax.x.set_spec(kp.special_x, labels=get_ksymbols(ksymbols))
    ax.y.set_label("Energy (eV)")
    # 36.0 is a base factor
    scale_plot = (kp.x[-1] - kp.x[0]) / len(kp.x) * 36.0 * scale
    _logger.info("scale set to %r", scale_plot)
    # draw zero line
    ax.axhline(0.0, ls="dashed")

    if apbs:
        _plot_pwav(ax, kp.x, bs, apbs, spin, scale_plot, prop_area=prop_area)

    # set limits
    if energy_range is not None:
        try:
            emin, emax = decode_float_ends(energy_range)
            ax.set_ylim(ymin=emin, ymax=emax)
            ax.tight_graph(xscale=None, yscale=None)
        except ValueError as err:
            raise ValueError("invalid energy range", energy_range) from err
    else:
        ax.tight_graph(xscale=None, yscale=1.2)

    p.write(file=output)
    if fig_ext is not None:
        p.savefig(get_filename_wo_ext(output) + "." + fig_ext)
