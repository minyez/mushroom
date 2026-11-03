"""Program-independent band, DOS and quasiparticle command interfaces."""
from pathlib import Path

import click

from mushroom.cli._utils import MultiValueCommand, multi_option, get_ksymbols

_engine = click.option("--engine", type=click.Choice(["plt", "grace"]), default="plt",
                       show_default=True, help="Plotting backend")
_output = click.option("-o", "output", default=None, help="Output image or Grace file")


def _reference(value):
    """Convert numeric command-line energy references."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return value


def _plt():
    """Import matplotlib only for a plotting command, with an actionable error."""
    try:
        import matplotlib.pyplot as plt
    except ImportError as err:
        raise click.ClickException("Install mushroom[plot] or use --engine grace") from err
    return plt


def _axes(engine, nrows=1):
    """Create axes with the selected backend."""
    if engine == "plt":
        return _plt().subplots(nrows, 1)
    from mushroom.visual.graceplot import Plot
    return Plot.subplots(nrows, 1)


def _finish(fig, engine, output, default, savefig=None):
    """Save or display a completed plot, including headless matplotlib fallback."""
    if engine == "grace":
        output = output or default + ".agr"
        # Keep portable-data round trips byte-identical across CLI processes.
        fig.set_timestamp("")
        fig.write(file=output)
        if savefig:
            fig.savefig(str(Path(output).with_suffix("." + savefig)))
        return
    from mushroom.visual.pyplot import is_interactive_backend
    plt = _plt()
    if savefig:
        click.echo("--savefig is ignored for matplotlib; use the extension of -o", err=True)
    if output is None and is_interactive_backend():
        plt.show()
    else:
        output = output or default + ".pdf"
        fig.savefig(output)
        click.echo("Saved {}".format(output))
    plt.close(fig)


def _labels(paths, labels):
    """Validate explicit labels or derive names from paths."""
    if labels and len(labels) != len(paths):
        raise click.UsageError("--labels must match the number of paths")
    return list(labels) or [Path(p).name for p in paths]


@click.command(cls=MultiValueCommand)
@click.argument("paths", nargs=-1, required=True)
@click.option("--code", help="Program that produced the data; infer from PATH when omitted")
@click.option("--kind", type=click.Choice(["ks", "gw", "qp", "exx"]), default="ks", help="Type of band energies to read")
@_engine
@_output
@click.option("--savefig", help="Convert Grace output to this image format")
@click.option("-e", "erange", help="Energy range in eV, e.g. m6~6")
@click.option("--ref", help="Energy reference: vbm, cbm, ef, none, a number, or is:ik:ib")
@click.option("--align", type=click.Choice(["vbm", "cbm", "ef", "none"]),
              help="Align each comparison dataset to this energy reference")
@click.option("--spin", type=click.Choice(["up", "dn", "both"]), default="both", help="Spin channel to plot")
@multi_option("--sym", help="Labels for special k points", metavar="SYMBOL...")
@multi_option("--labels", help="Dataset labels in path order", metavar="LABEL...")
@multi_option("--apb", help="Atom:projector:band selections for fat bands", metavar="APB...")
@click.option("--scale", type=float, default=1., help="Scale of fat-band marker diameters")
@click.option("--area", is_flag=True, help="Make marker area proportional to projector weight")
@click.option("--dos", "dospath", help="DOS path for a combined band and DOS plot")
@multi_option("--aps", help="Atom:projector selections for projected DOS", metavar="AP...")
@click.option("--data", is_flag=True, help="Print or export numeric data without plotting")
@click.option("--save", type=click.Path(), help="Save parsed data as a portable NumPy archive")
def band(paths, code, kind, engine, output, savefig, erange, ref, align, spin, sym,
         labels, apb, scale, area, dospath, aps, data, save):
    """Read, analyze and plot band data from PATHS or portable archives."""
    from mushroom.io import read_band, read_dos
    from mushroom.core.bs import display_band_analysis
    from mushroom.core.ioutils import decode_float_ends
    from mushroom.visual.bandplot import plot_band, plot_fatband, plot_bands_compare, plot_band_dos
    from mushroom.visual.axes import wrap_axes

    labels = _labels(paths, labels)
    if ref is not None and align is not None:
        raise click.UsageError("--ref and --align are mutually exclusive")
    if len(paths) > 1 and (apb or dospath or save or ref is not None):
        raise click.UsageError("--apb, --dos, --save and --ref require a single path")
    if len(paths) == 1 and align is not None:
        raise click.UsageError("Use --ref for a single path")
    items = [read_band(p, code=code, kind=kind, projections=bool(apb)) for p in paths]
    for item in items:
        item.bs.unit = "ev"
    if save:
        items[0].save(save)
    if data:
        for item in items:
            display_band_analysis(item.bs, item.kpts)
        return
    if engine == "plt":
        _plt()
    ref = _reference(ref) if ref is not None else "vbm"
    limits = decode_float_ends(erange) if erange else (-6., 6.)
    selected_spin = {"up": 0, "dn": 1, "both": None}[spin]
    item = items[0]
    symbols = get_ksymbols(sym) or item.ksymbols
    if dospath:
        fig, (ax, _) = plot_band_dos(item.bs, item.kpath(), read_dos(dospath, code=code),
                                    engine=engine, ref=ref, aps=aps, erange=limits, ksymbols=symbols, spin=selected_spin)
    else:
        fig, ax = _axes(engine)
        if len(items) > 1:
            plot_bands_compare(ax, [(d.bs, d.kpath(), label) for d, label in zip(items, labels)],
                               align=align or "vbm", ksymbols=symbols, spin=selected_spin)
        else:
            plot_band(ax, item.bs, item.kpath(), ref=ref,
                      spin={"up": 0, "dn": 1, "both": None}[spin], ksymbols=symbols)
        wrap_axes(ax).set_ylim(*limits)
    if apb:
        for isp in range(item.bs.nspins) if spin == "both" else [{"up": 0, "dn": 1}[spin]]:
            plot_fatband(ax, item.bs, item.kpath(), apb, spin=isp, ref=ref, scale=scale, prop_area=area)
    _finish(fig, engine, output, "plotband", savefig)


@click.command(cls=MultiValueCommand)
@click.argument("paths", nargs=-1, required=True)
@click.option("--code", help="Program that produced the data; infer from PATH when omitted")
@_engine
@_output
@click.option("--savefig", help="Convert Grace output to this image format")
@click.option("-e", "erange", help="Energy range in eV, e.g. m6~6")
@click.option("--ref", default="ef", help="DOS energy reference: ef or a number in eV")
@click.option("--spin", type=click.Choice(["up", "dn", "both"]), default="both", help="Spin channel to plot")
@multi_option("--aps", help="Atom:projector selections for projected DOS", metavar="AP...")
@click.option("--sigma", type=float, default=.05, help="Gaussian DOS broadening in eV for band inputs")
@multi_option("--labels", help="Dataset labels in path order", metavar="LABEL...")
@click.option("--data", is_flag=True, help="Print or export numeric data without plotting")
@click.option("--save", type=click.Path(), help="Save parsed data as a portable NumPy archive")
def dos(paths, code, engine, output, savefig, erange, ref, spin, aps, sigma, labels, data, save):
    """Read, export and plot densities of states from PATHS."""
    from mushroom.io import read_dos
    from mushroom.visual.dosplot import plot_dos, export_tdos_data, export_pdos_data
    from mushroom.visual.axes import wrap_axes, DEFAULT_COLORS
    from mushroom.core.ioutils import decode_float_ends

    labels = _labels(paths, labels) if labels or len(paths) > 1 else ["Total"]
    if save and len(paths) != 1:
        raise click.UsageError("--save requires a single path")
    items = [read_dos(p, code=code, sigma=sigma) for p in paths]
    for item in items:
        item.unit = "ev"
    if save:
        items[0].save(save)
    if data:
        tlines, plines = [], []
        for item in items:
            tlines.extend(export_tdos_data(item))
            if aps:
                plines.extend(export_pdos_data(item, aps, {"up": 0, "dn": 1, "both": None}[spin]))
        Path("tdos.dat").write_text("\n".join(tlines) + "\n")
        if plines:
            Path("pdos.dat").write_text("\n".join(plines) + "\n")
        return
    fig, ax = _axes(engine)
    for i, (item, label) in enumerate(zip(items, labels)):
        plot_dos(ax, item, aps=aps, ref=_reference(ref),
                 spin={"up": 0, "dn": 1, "both": None}[spin], label_total=label,
                 colors=[DEFAULT_COLORS[i % len(DEFAULT_COLORS)]] if len(items) > 1 else None)
    if erange:
        wrap_axes(ax).set_xlim(*decode_float_ends(erange))
    wrap_axes(ax).legend()
    _finish(fig, engine, output, "plotdos", savefig)


@click.command("qp-corr")
@click.argument("path")
@click.option("--code", help="Program that produced the data; infer from PATH when omitted")
@click.option("--ref", type=click.Choice(["vbm", "ef", "none"]), default="none",
              help="Reference for KS energies on the horizontal axis")
@click.option("--fit", "fit_requested", is_flag=True, help="Fit occupied and empty QP corrections separately")
@click.option("--emin", type=float, help="Minimum KS energy in eV after reference subtraction")
@click.option("--emax", type=float, help="Maximum KS energy in eV after reference subtraction")
@_engine
@_output
@click.option("--data", is_flag=True, help="Print or export numeric data without plotting")
def qp_corr(path, code, ref, fit_requested, emin, emax, engine, output, data):
    """Plot or print quasiparticle corrections from PATH."""
    from mushroom.io import read_qp_pair
    from mushroom.core.bs import qp_correction, fit_qp_correction
    from mushroom.visual.bandplot import plot_qp_correction

    e, de, occupied = qp_correction(*read_qp_pair(path, code=code), ref=ref)
    mask = (e >= emin if emin is not None else e == e) & (e <= emax if emax is not None else e == e)
    e, de, occupied = e[mask], de[mask], occupied[mask]
    fit = fit_qp_correction(e, de, occupied) if fit_requested else None
    if data:
        for values in zip(e, de, occupied.astype(int)):
            click.echo("{:.8f} {:.8f} {:d}".format(*values))
        if fit:
            click.echo(str(fit))
        return
    fig, ax = _axes(engine)
    plot_qp_correction(ax, e, de, occupied, fit=fit)
    _finish(fig, engine, output, "plot_qpcorr")


@click.command(cls=MultiValueCommand)
@click.argument("path")
@click.option("--code", help="Program that produced the data; infer from PATH when omitted")
@multi_option("--band", "band_ids", help="Band indices or identifiers, e.g. vbm cbm", metavar="BAND...")
@click.option("--k", "ik", type=int, help="Zero-based k-point index; select the band extremum when omitted")
@click.option("--spin", "ispin", type=int, default=0, help="Zero-based spin channel index")
@click.option("-n", "npoints", type=int, default=5, help="Maximum points per side, including the extremum")
def emass(path, code, band_ids, ik, ispin, npoints):
    """Fit signed effective masses along the band path near an extremum."""
    from mushroom.io import read_band
    from mushroom.core.bs import effective_mass
    data = read_band(path, code=code)
    for band_id in band_ids or ("vbm", "cbm"):
        result = effective_mass(data.bs, data.kpath(), band_id, ik, ispin=ispin, npoints=npoints)
        index = result["ik"]
        click.echo("{} k={} {} left={} ({}) right={} ({})".format(
            band_id, index, data.kpts[index].tolist(), result["left"], result["left_label"],
            result["right"], result["right_label"]))
