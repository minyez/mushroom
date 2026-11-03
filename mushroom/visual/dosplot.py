"""Portable DOS plots and legacy-compatible text exports."""
from numbers import Real
from mushroom.core.data import export_2d_data
from mushroom.core.dos import split_ap
from mushroom.visual.axes import wrap_axes, DEFAULT_COLORS


def plot_dos(ax, dos, *, aps=(), spin=None, ref='efermi', orientation='horizontal',
             show_total=True, reverse_spindn=True, colors=None, fill=False, label_total='Total'):
    """Plot total/projected DOS, with negative spin-down curves by default."""
    adapter = wrap_axes(ax)
    if orientation not in ('horizontal', 'vertical'):
        raise ValueError('orientation must be horizontal or vertical')
    if spin is not None and spin not in [-1] + list(range(dos.nspins)):
        raise ValueError('Invalid spin {}'.format(spin))
    if ref in ('efermi', 'ef', 'fermi'):
        reference = dos.efermi
    elif ref is None or isinstance(ref, Real):
        reference = ref or 0.
    else:
        raise ValueError('DOS reference must be efermi, a number, or None')
    total_color = 'black' if colors is None else colors[0]
    colors = DEFAULT_COLORS if colors is None else colors
    groups = [(None, None, label_total, total_color)] if show_total else []
    for i, ap in enumerate(aps):
        atm, prj = split_ap(ap)
        groups.append((atm, prj, '-'.join(ap.split(':')), colors[i % len(colors)]))
    energy = dos.egrid - reference
    for ig, (atm, prj, label, color) in enumerate(groups):
        for isp in range(dos.nspins) if spin is None else [spin]:
            values = dos.get_tdos(isp) if show_total and ig == 0 else dos.get_pdos(isp, atm, prj)
            if isp == 1 and reverse_spindn:
                values = -values
            x, y = (energy, values) if orientation == 'horizontal' else (values, energy)
            legend = label if spin is not None or isp == 0 else None
            adapter.line(x, y, color=color, label=legend)
            if fill:
                if orientation == 'vertical' and adapter.engine == 'plt':
                    adapter.fill_betweenx(energy, values, color=color, alpha=.3)
                else:
                    adapter.fill_between(x, y, color=color, alpha=.3)
    energy_label = 'Energy ({})'.format({'ev': 'eV', 'ry': 'Ry', 'au': 'Ha'}.get(dos.unit, dos.unit))
    adapter.set_xlabel(energy_label if orientation == 'horizontal' else 'DOS')
    adapter.set_ylabel('DOS' if orientation == 'horizontal' else energy_label)
    return ax


def export_tdos_data(dos) -> list[str]:
    """Return legacy tdos.dat lines on the original absolute energy grid."""
    return ['#fermi-energy: {}'.format(dos.efermi)] + export_2d_data(
        [dos.egrid, dos.get_tdos(ispin=-1)], transpose=True)


def export_pdos_data(dos, aps, spin=None) -> list[str]:
    """Return legacy pdos.dat lines with Fermi header and blank separators."""
    lines = ['#fermi-energy: {}'.format(dos.efermi)]
    for ap in aps:
        atm, prj = split_ap(ap)
        lines.append('#atom-projector:{}'.format(ap))
        lines.extend(export_2d_data([dos.egrid, dos.get_pdos(spin, atm, prj)], transpose=True))
        lines.append('')
    return lines
