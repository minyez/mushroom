# -*- coding: utf-8 -*-
"""FHI-aims commands

Modules heavier than click are imported inside the commands to keep the entry fast.
"""
import os
import sys
from types import SimpleNamespace

import click

from mushroom.cli._utils import Group, check_exclusive, multi_option, opt_trans, optional_value_option

_opt_unit = click.option("--unit", default="ev", help="energy unit")
_opt_remove_k_before = click.option("--rkbf", "remove_k_before", type=int, default=0,
                                    help="number of kpoints at first to remove")
_opt_remove_k_behind = click.option("--rkbh", "remove_k_behind", type=int, default=None,
                                    help="number of kpoints from behind to remove")
_opt_use_occ_only = click.option(
    "--use-occ-only", is_flag=True,
    help="only use occupation number to detect band edges, instead of using both energy and occ")


@click.group(cls=Group)
def aims():
    """FHI-aims utilities"""


@aims.command("append-basis")
@click.argument("control_file")
@click.argument("directory")
@click.option("--sd", "species_defaults", default=None, help="species_defaults directory")
@multi_option("-e", "elements", metavar="ELEM...", help="Elements to add")
@optional_value_option("-i", "pgeometry", const="geometry.in", default=None,
                       help="geometry file to load elements")
@click.pass_context
def append_basis(ctx, control_file, directory, species_defaults, elements, pgeometry):
    """append aims basis to CONTROL_FILE from the basis DIRECTORY"""
    from mushroom.aims import get_atoms_from_geometry
    from mushroom.aims.input import divide_control_lines
    from mushroom.aims.species import (get_basis_directory_from_alias, readlines_species_defaults,
                                       search_basis_directories)

    check_exclusive(ctx, "elements", "pgeometry")
    elements = list(elements)
    if not elements:
        if pgeometry is None:
            raise click.UsageError("specify elements either by -e or -i", ctx=ctx)
        elements = list(set(get_atoms_from_geometry(pgeometry)))

    try:
        directory = get_basis_directory_from_alias(directory)
    except ValueError as err:
        basis_avail = search_basis_directories(species_defaults)
        if directory not in basis_avail:
            raise ValueError("Basis {} is not available".format(directory)) from err

    print("Appending elements {} from {} to {}".format(elements, directory, control_file))
    sl = readlines_species_defaults(directory, *elements, species_defaults=species_defaults)

    if os.path.exists(control_file):
        regions = divide_control_lines(control_file)
        gl = regions[0]
        if len(regions) > 1:
            print("Replacing existing basis information in control file {}".format(control_file))
        ctrl_new = "".join(gl) + sl
    else:
        ctrl_new = sl

    with open(control_file, 'w') as h:
        print(ctrl_new, file=h)


def _get_reference(bs, vbm_zero, cbm_zero, fermi_zero, isikib_zero):
    """get the energy reference of a band structure"""
    ref = 0.0
    if vbm_zero:
        ref = bs.vbm
    if cbm_zero:
        ref = bs.cbm
    if fermi_zero:
        ref = bs.efermi
    if isikib_zero:
        ispin, ikpt, ib = isikib_zero.split(":")
        ref = bs.get_eigen(ib)[int(ispin), int(ikpt), 0]
    return ref


@aims.command()
@click.argument("out_files", nargs=-1, required=True)
@multi_option("--compare", metavar="FILE...",
              help="band output files to overlay as red dashed lines; use the same k path, "
                   "with the selected energy-zero option applied independently")
@_opt_unit
@click.option("-o", "output", default="plotband",
              help="file name of the figure to save (arg file for grace engine)")
@click.option("--data", "data_only", is_flag=True, help="only extract and print data, do not plot")
@_opt_remove_k_before
@_opt_remove_k_behind
@click.option("--geo", "geometry", default="geometry.in", help="geometry.in file")
@click.option("--savefig", "fig_ext", default=None, help="figure extension to convert")
@click.option("-e", "energy_range", default=None,
              help="energy range (y-axis), e.g. 'm8~5' for -8.0 to 5.0")
@click.option("--bands", "band_erange", default=None,
              help="range of bands to plot, e.g. ~m2 for bands except the highest two")
@multi_option("--resolve", metavar="BANDS...", help="resolve band crossing, e.g. 5,6,7")
@click.option("--no-band-line", is_flag=True, help="do not draw band lines, use marker")
@_opt_use_occ_only
@click.option("--engine", default="grace", type=click.Choice(["grace", "plt"]),
              help="plot engine, grace/matplotlib(plt)")
@click.option("--marker", default="none", help="marker")
@click.option("--ms", "marker_size", type=float, default=1.0, help="marker size")
@multi_option("--resolve-dthres", "deriv_thres", type=float, metavar="THRES...",
              help="derivative threshold for band resolution. "
                   "Try some negative value when you need resolution earlier")
@click.option("--transparent", is_flag=True, help="Set background of Grace graph to transparent")
@opt_trans
@click.option("-v", "--value", "value_only", is_flag=True,
              help="show values only when displaying band")
@click.option("--rmbs", type=int, default=None, help="Number of lowest bands to prune")
@click.option("--rmbe", type=int, default=None, help="Number of highest bands to prune")
@click.option("--ef", "efermi", type=float, default=None, help="Fermi energy")
@click.option("-n", "n_states", type=int, default=None, help="Force occupation of first n states")
@click.option("--skbz", "isikib_zero", default=None,
              help="use enk as energy zero, 'is:ik:ib', ib as a band identifier")
@click.option("--ferz", "fermi_zero", is_flag=True, help="use Fermi energy as energy zero")
@click.option("--vbmz", "vbm_zero", is_flag=True, help="use VBM as energy zero")
@click.option("--cbmz", "cbm_zero", is_flag=True, help="use CBM as energy zero")
@multi_option("--sym", "ksymbols", metavar="SYMBOL...",
              help="Symbols of high symmetry points, overwrite control")
@optional_value_option("--sym-cf", "ksymbols_cf", const="control.in", default=None,
                       help="read ksymbols in band output from the path to the control file")
@click.pass_context
def band(ctx, **kwargs):
    """extract the band energies from aims output"""
    import matplotlib.pyplot as plt
    from matplotlib.ticker import MultipleLocator

    from mushroom.aims.band import read_band_output
    from mushroom.aims.input import Control, get_path_ksymbols
    from mushroom.core.bs import (display_band_analysis, display_transition_energies,
                                  resolve_band_crossing)
    from mushroom.core.cell import Cell
    from mushroom.core.ioutils import decode_float_ends, decode_int_ends, get_filename_wo_ext
    from mushroom.core.kpoints import KPathLinearizer
    from mushroom.visual.graceplot import Plot
    from mushroom.visual.pyplot import rc_gracify

    check_exclusive(ctx, "efermi", "n_states")
    check_exclusive(ctx, "isikib_zero", "fermi_zero", "vbm_zero", "cbm_zero")
    check_exclusive(ctx, "ksymbols", "ksymbols_cf")
    args = SimpleNamespace(**kwargs)
    rc_gracify()

    bs, kpts = read_band_output(*args.out_files, unit=args.unit,
                                filter_k_before=args.remove_k_before,
                                filter_k_behind=args.remove_k_behind, use_occ_only=args.use_occ_only)

    # reset the occupation numbers by Fermi energy
    if args.efermi is not None or args.n_states is not None:
        bs.reset_occupations(efermi=args.efermi, n_states=args.n_states)

    bs.prune_bands(args.rmbs, args.rmbe)

    nbands = bs.nbands
    try:
        c = Cell.read(args.geometry, format="aims")
        recp_latt = c.b
    except FileNotFoundError:
        recp_latt = None

    display_band_analysis(bs, kpts, value_only=args.value_only)
    if args.trans:
        display_transition_energies(args.trans, bs, kpts, value_only=args.value_only)

    if args.data_only:
        return
    ref = _get_reference(bs, args.vbm_zero, args.cbm_zero, args.fermi_zero, args.isikib_zero)

    kp = KPathLinearizer(kpts, recp_latt)
    if args.compare:
        bs_compare, kpts_compare = read_band_output(
            *args.compare, unit=args.unit,
            filter_k_before=args.remove_k_before,
            filter_k_behind=args.remove_k_behind, use_occ_only=args.use_occ_only)
        if args.efermi is not None or args.n_states is not None:
            bs_compare.reset_occupations(efermi=args.efermi, n_states=args.n_states)
        bs_compare.prune_bands(args.rmbs, args.rmbe)
        ref_compare = _get_reference(bs_compare, args.vbm_zero, args.cbm_zero,
                                     args.fermi_zero, args.isikib_zero)
        kp_compare = KPathLinearizer(kpts_compare, recp_latt)
        eigen_compare = bs_compare.eigen[0, :, :] - ref_compare

    if args.band_erange is not None:
        band_lb, band_ub = decode_int_ends(args.band_erange)

    eigen = bs.eigen[0, :, :]
    if args.resolve:
        if not args.deriv_thres:
            deriv_thres = [None,] * len(args.resolve)
        else:
            if len(args.deriv_thres) == 1:
                deriv_thres = [args.deriv_thres[0],] * len(args.resolve)
            elif len(args.deriv_thres) == len(args.resolve):
                deriv_thres = args.deriv_thres
            else:
                raise ValueError(
                    "deriv_thres should be either one number, or the same length as resolve")
        for resband, thres in zip(args.resolve, deriv_thres):
            bands_tuple = tuple(map(int, resband.split(',')))
            eigen[:, bands_tuple] = resolve_band_crossing(
                kp.x, eigen[:, bands_tuple], deriv_thres=thres)

    marker = args.marker
    ls = None
    if args.no_band_line:
        ls = "none"
        if marker == "none":
            marker = "o"

    ksymbols = None
    if args.ksymbols:
        ksymbols = list(args.ksymbols)
        if len(args.ksymbols) == 1:
            ksymbols = args.ksymbols[0].split()

    if args.ksymbols_cf is not None:
        c_ksym = Control.read(args.ksymbols_cf)
        band_c_ksym = c_ksym.get_output("band", None)
        if band_c_ksym is None:
            raise ValueError("%s does not include output band" % args.ksymbols_cf)
        ksymbols = get_path_ksymbols(band_c_ksym)

    if ksymbols is not None and len(kp.special_x) != len(ksymbols):
        print(ksymbols)
        print(kp.special_x)
        raise ValueError(
            "Number of k segments different from number of symbols! Contact developer")

    # check non-continuous special kx
    x_break = []
    ksym_break = []
    if ksymbols is not None:
        for x, ksym in zip(kp.special_x, ksymbols):
            if "|" in ksym:
                x_break.append(x)
                ksym_break.append(ksym)

    if args.energy_range is not None:
        try:
            emin, emax = decode_float_ends(args.energy_range)
        except ValueError as err:
            raise ValueError(f'invalid energy range: {args.energy_range}') from err
    else:
        emin = -20
        emax = 20

    if args.engine == "grace":
        fig, ax = Plot.subplots(1, 1, background=not args.transparent)
        ax.plot(kp.x, eigen.transpose() - ref, color="k",
                symbol=marker, ls=ls, ssize=args.marker_size)
        if args.compare:
            ax.plot(kp_compare.x, eigen_compare.transpose(), color="red", ls="--")
        ax.x.set_major(grid=True, size=0.0, color="grey", lw=3, ls="longdashed")
        ax.x.set_spec(kp.special_x, labels=ksymbols)

        if len(ksym_break) > 0:
            ax.altx.set(switch="on")
            ax.altx.set_bar(switch="off")
            ax.altx.set_tick(switch="off")
            ax.altx.set_ticklabel(switch="off")
            ax.altx.set_spec(x_break, labels=ksym_break)
            ax.altx.set_major(grid=True, size=0.0, color="black", lw=3, ls="solid")
        ax.y.set_major(major=4)
    else:
        fig, ax = plt.subplots(1, 1, figsize=(8, 8))
        for iband in range(nbands):
            ax.plot(kp.x, eigen[:, iband] - ref, color="k",
                    marker=marker, ls=ls, ms=args.marker_size)
        if args.compare:
            ax.plot(kp_compare.x, eigen_compare, color="red", ls="--")
        if ksymbols is not None:
            ksymbols = ["$" + x + "$" for x in ksymbols]
        ax.xaxis.set_ticks(kp.special_x, labels=ksymbols)
        ax.xaxis.grid(color='grey', ls="--")
        ax.set_axisbelow(True)
        ax.yaxis.set_major_locator(MultipleLocator(4))

    # draw zero line
    ax.axhline(0.0, ls="--", color="k")
    # slightly wider than the last symbol to make it visible on graph
    ax.set_xlim(0.0, kp.x[-1] + 0.0001)
    ax.set_ylim(ymin=emin, ymax=emax)
    ax.set_ylabel("Energy [eV]")

    if args.engine == "grace":
        fig.write(file=args.output + ".agr")
    elif args.fig_ext is None:
        plt.show()

    if args.fig_ext is not None:
        fn = get_filename_wo_ext(args.output) + "." + args.fig_ext
        fig.savefig(fn, dpi=300)


@aims.command("check-finish")
@click.option("-d", "directory", default=".", show_default=True,
              help="the path of directory to check")
@click.option("-o", "aimsout_pat", default="aims.out*", show_default=True,
              help="the pattern of aimsout to check")
def check_finish(directory, aimsout_pat):
    """check if at least one FHI-aims calculation in the directory is finished"""
    from mushroom.aims.analyse import is_finished_aimsdir

    f = is_finished_aimsdir(directory, aimsout_pat=aimsout_pat)
    if f is None:
        sys.exit(1)
    print(f)


def _handle_tag_pair(tag_pair):
    """split 'tag:value', with value converted to bool when it is a Fortran-like logical"""
    tv = tag_pair.split(':', maxsplit=1)
    try:
        t, v = tv
    except ValueError:
        t = tv[0]
        v = None
    if v is not None:
        if v.lower() in ['t', '.t.', '.true.', 'true']:
            v = True
        elif v.lower() in ['f', '.f.', '.false.', 'false']:
            v = False
    return t, v


def _handle_elem_tag_pair(elem_tag_pair):
    """split 'elem:tag:value'"""
    etv = elem_tag_pair.split(':', maxsplit=1)
    try:
        e, tv = etv
    except ValueError as err:
        raise ValueError(f"invalid elem:tag:value pair: {elem_tag_pair}") from err
    t, v = _handle_tag_pair(tv)
    return e, t, v


@aims.command()
@click.option("-O", "output", default=None, help="the filename to dump the control")
@click.option("-i", "control_temp", default=None, help="template to initialize the control")
@multi_option("-t", "tags", metavar="TAG:VALUE...", help="tag pair in 'tag:value' format")
@multi_option("--ot", "output_tags", metavar="TAG...", help="output tags")
@multi_option("--st", "species_tags", metavar="ELEM:TAG:VALUE...",
              help="species tags in 'elem:tag:value' format")
@click.option("-s", "species", default="defaults_2020", help="species category")
@click.option("--sl", "species_level", default="intermediate",
              help="species accuracy level, e.g. light, tight")
@multi_option("-e", "elements", metavar="ELEM...", help="the elements in species setup")
@multi_option("--handle-basis", metavar="X:ARGS...", help="handle the basis, see description")
@click.option("--reload-species", default=None,
              help="reload species from file. remove all species data if set to ''")
def control(output, control_temp, tags, output_tags, species_tags, species, species_level,
            elements, handle_basis, reload_species):
    """create the aims control object and dump to file

    Allow the user to handle the basis functions and ABFs in the species setup,
    by using the ``--handle-basis`` options, respectively.
    The option value should be a string like "x:arg1:arg2:...".
    The letter "x" should be a, m or d, corresponding to ``add_basis``, ``modify_basis``,
    and ``delete_basis`` methods of the ``Species`` object.
    The left string is splited by ``:`` and parsed in the same order to the method.

    Currently a template including the species is required.
    """
    from mushroom.aims.input import Control
    from mushroom.aims.species import Species

    if control_temp is None:
        raise NotImplementedError("please parse the template")
    c = Control.read(control_temp)
    if reload_species is not None:
        c.purge_species()
        if reload_species != "":
            ss = Species.read_multiple(reload_species)
            c.add_species(*ss)
    for t in tags:
        c.update_tag(*_handle_tag_pair(t))
    for t in output_tags:
        c.update_output_tag(*_handle_tag_pair(t))
    for t in species_tags:
        c.update_species_basic_tag(*_handle_elem_tag_pair(t))

    # handle basis
    for hb in handle_basis:
        bargs = hb.split(':')
        f = {"a": c.add_basis, "m": c.modify_basis, "d": c.delete_basis}.get(bargs[0], None)
        if f is None:
            raise ValueError(f"Support basis method a/m/d, parsed: {bargs[0]}")
        f(*bargs[1:])

    c.write(sys.stdout if output is None else output)


@aims.command()
@click.argument("aimsout")
def dim(aimsout):
    """print the dimensions of the calculation from aims stdout file"""
    from mushroom.aims.analyse import get_dimensions

    format_str, dict_str_dim = get_dimensions(aimsout)
    for sd in dict_str_dim.items():
        if sd[1] is not None:
            print(format_str % sd)
        else:
            print(format_str % (sd[0], "(NOT FOUND)"))


@aims.command()
@click.argument("out_files", nargs=-1, required=True)
@_opt_unit
@opt_trans
@_opt_remove_k_before
@_opt_remove_k_behind
def gap(out_files, unit, trans, remove_k_before, remove_k_behind):
    """compute the band gap from aims band output"""
    from mushroom.aims.band import read_band_output
    from mushroom.core.bs import display_band_analysis, display_transition_energies

    bs, kpts = read_band_output(*out_files, unit=unit,
                                filter_k_before=remove_k_before,
                                filter_k_behind=remove_k_behind)
    display_band_analysis(bs, kpts)
    if trans:
        display_transition_energies(trans, bs, kpts)


@aims.command("get-input")
@click.argument("aimsout")
@click.option("-c", "output_ctrl", default="control.in",
              help="output path for extracted control file")
@click.option("-g", "output_geom", default="geometry.in",
              help="output path for extracted geometry file")
@click.option("-f", "force", is_flag=True, help="force overwrite")
def get_input(aimsout, output_ctrl, output_geom, force):
    """Extract input files, namely control.in and geometry.in from an aims stdout file"""
    from mushroom.aims.stdout import StdOut

    stdout = StdOut(aimsout)

    ctrl = stdout.get_control()
    if os.path.exists(output_ctrl):
        if force:
            print("Overwriting", output_ctrl)
            ctrl.write(output_ctrl)
        else:
            print(output_ctrl, "exists, skip exporting control.in file")
    else:
        print("Writing", output_ctrl)
        ctrl.write(output_ctrl)

    geom = stdout.get_geometry()
    if os.path.exists(output_geom):
        if force:
            print("Overwriting", output_geom)
            geom.write("aims", output_geom)
        else:
            print(output_geom, "exists, skip exporting geometry.in file")
    else:
        print("Writing", output_geom)
        geom.write("aims", output_geom)


@aims.command("prepare-control")
@click.option("--xc", default="pbe", help="Functional")
@click.option("-s", "--spin", is_flag=True, help="Spin setup")
@click.option("--template", default=None, help="Template for general and output tags")
@click.option("-g", "path_geometry", default=None, help="Path to geometry file")
@click.option("--sp", "--species", "species", default="intermediate", help="Species default")
@click.option("-k", "--kgrids", nargs=3, type=int, default=None, help="k-point mesh")
def prepare_control(xc, spin, template, path_geometry, species, kgrids):
    """prepare a control.in file and print it"""
    from mushroom.aims.input import Control, read_geometry

    if path_geometry is not None:
        geo = read_geometry(path_geometry)
        elems = geo.atom_types
        # TODO: the underlying Cell class of read_geometry only supports periodic case
        periodic = True
    else:
        elems = None
        periodic = True
        if kgrids is not None:
            periodic = False
    c = Control.default(periodic=periodic, spin=spin)
    # Update general and output tags from the template
    if template is not None:
        c_temp = Control.read(template)
        c.update_tags(c_temp.tags)
        c.update_output_tags(c_temp.output)

    c.set_xc(xc)
    if kgrids is not None:
        k_grid_str = "{} {} {}".format(*kgrids)
        c.update_tag("k_grid", k_grid_str)

    # Add species defaults
    if elems is not None:
        c.add_default_species(species, *elems)
    print(c)


@aims.command("qp-corr")
@click.argument("aimsout")
@click.option("-o", "output_agr", default=None, help="path of grace output")
@click.option("--kind", default="qp", type=click.Choice(["x", "c", "xc", "qp"]),
              help="type of QP correction, default QP")
@click.option("--emin", "eksmin", type=float, default=None,
              help="minimal KS energy to show on plot")
@click.option("--emax", "eksmax", type=float, default=None,
              help="maximal KS energy to show on plot")
@click.option("--ref", "refopt", default=None, type=click.Choice(["vbm", "fermi"]),
              help="reference as energy (absicca) zero")
def qp_corr(aimsout, output_agr, kind, eksmin, eksmax, refopt):
    """compute and plot QP energy correction from aims stdout file"""
    from mushroom.aims.analyse import StdOut
    from mushroom.visual.graceplot import Plot

    s = StdOut(aimsout)
    eks, _ = s.get_QP_bandstructure("eps")

    ref = 0.0
    if refopt == "vbm":
        ref = eks.vbm
    elif refopt == "fermi":
        ref = eks.efermi

    fig, ax = Plot.subplots(1, 1)
    ax.set_xlabel("Kohn-Sham energy [eV]")
    if kind == "c":
        data = s.get_QP_sigc()
        ax.set_ylabel("Correlation self-energy [eV]")
    elif kind == "x":
        data = s.get_QP_sigx()
        ax.set_ylabel("Exchange self-energy [eV]")
    elif kind == "xc":
        d, _ = s.get_QP_result()
        data = d["sigc"] + d["exx"]
        ax.set_ylabel("XC self-energy [eV]")
    else:
        d, _ = s.get_QP_result()
        data = d["sigc"] + d["exx"] - d["vxc"]
        ax.set_ylabel("Self-energy correction to KS state [eV]")

    ax.plot_group(eks.eigen - ref, data, color="k", ls="none", ssize=0.55)
    ax.tight_graph()

    # draw reference
    ax.axhline(0.0, ls="dashed", color="gray")
    ax.axvline(0.0, ls="dashed", color="gray")

    if output_agr is None:
        output_agr = {
            "x": "plot_sigx.agr",
            "c": "plot_sigc.agr",
            "xc": "plot_sigxc.agr",
            "qp": "plot_qpcorr.agr",
        }.get(kind)
    fig.write(output_agr)


@aims.command("qp-dos")
@click.argument("stdout")
@click.option("-s", "sigma", type=float, default=0.05, help="smearing, default 0.05")
@click.option("-o", "output", default="dos.dat", help="output filename")
@click.option("--filter-below-ef", type=float, default=10,
              help="states more than it below the Fermi level will not be added to DOS")
@click.option("--ks", is_flag=True, help="KS dos instead of QP")
@click.option("--filter-above-ef", type=float, default=None,
              help="similar to --filter-below-ef, but for those above Fermi")
def qp_dos(stdout, sigma, output, filter_below_ef, ks, filter_above_ef):
    """export the QP density of states from aims standard output

    This is done by smearing the QP energies according to Gaussian function.
    The name of file storing the DOS data is controled by ``-o`` option.
    """
    from mushroom.aims.analyse import StdOut

    s = StdOut(stdout)
    bs, _ = s.get_QP_bandstructure("eps" if ks else "eqp")
    print(f"Fermi energy (QP): {bs.efermi} {bs.unit}")
    # filter states
    emax = None
    if filter_above_ef:
        emax = bs.efermi + filter_above_ef
    dos = bs.get_dos(emin=bs.efermi - filter_below_ef, emax=emax, sigma=sigma)
    print(f"Smearing: {sigma} {bs.unit}")
    with open(output, 'w') as h:
        def p(*args):
            print(*args, file=h)
        if ks:
            p(f"#KS-DOS from {stdout}")
        else:
            p(f"#QP-DOS from {stdout}")
        p(f"#EF: {bs.efermi} {bs.unit}")
        p(f"#Sigma: {sigma}")
        p("\n".join(dos.export_tdos(transpose=True, reverse_spindn=True)))


@aims.command("qp-gap")
@click.argument("stdout")
@opt_trans
@click.option("--ks", is_flag=True, help="KS gap instead of QP")
@click.option("-v", "--value", "value_only", is_flag=True, help="Value only")
@_opt_use_occ_only
def qp_gap(stdout, trans, ks, value_only, use_occ_only):
    """analyze the QP energies from aims stdout file"""
    from mushroom.aims.analyse import StdOut
    from mushroom.core.bs import display_band_analysis, display_transition_energies

    s = StdOut(stdout)
    bs, kpts = s.get_QP_bandstructure("eps" if ks else "eqp", use_occ_only=use_occ_only)
    display_band_analysis(bs, kpts, value_only=value_only)
    if trans:
        display_transition_energies(trans, bs, kpts, value_only=value_only)
