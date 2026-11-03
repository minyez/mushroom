# -*- coding: utf-8 -*-
"""Program-independent band plots with matplotlib and Grace backends."""
import warnings
from typing import Union
from collections.abc import Iterable
import numpy as np
try:
    import matplotlib.pyplot as plt
except ImportError:
    plt = None
from mushroom.core.utils import raise_no_module
from mushroom.core.bs import (BandStructure, BandPathData, get_energy_reference,
                              split_apb, resolve_band_crossing)
from mushroom.core.kpoints import KPathLinearizer, format_ksymbols, split_kpath_breaks
from mushroom.core.data import export_2d_data
from mushroom.core.logger import loggers
from mushroom.visual.axes import wrap_axes, DEFAULT_COLORS

_logger = loggers['bs']
__all__ = ['plot_band', 'plot_fatband', 'export_fatband_data', 'plot_bands_compare',
           'plot_band_dos', 'plot_qp_correction', 'bandplot']


def plot_band(ax, bs, kp, *, ref='vbm', spin=None, bands=None,
              color=None, color_dn=None, ls='solid', ls_dn='dashed', lw=None,
              marker='none', ms=None, label=None, ksymbols=None,
              set_xaxis=True, set_ylabel=True, zero_line=True, resolve=None):
    """Plot selected bands and spins using one common absolute energy reference."""
    adapter = wrap_axes(ax)
    if spin is not None and spin not in range(bs.nspins):
        raise ValueError('Invalid spin {} for nspins={}'.format(spin, bs.nspins))
    indices = np.arange(bs.nbands)
    if isinstance(bands, tuple):
        indices = indices[slice(*bands)]
    elif bands is not None:
        indices = indices[list(bands)]
    reference = get_energy_reference(bs, ref)
    for isp in range(bs.nspins) if spin is None else [spin]:
        eigen = bs.eigen[isp].copy()
        for selected, threshold in resolve or ():
            eigen[:, selected] = resolve_band_crossing(kp.x, eigen[:, selected], deriv_thres=threshold)
        col = color or ('black' if bs.nspins == 1 else 'blue')
        style = ls
        legend = label
        if bs.nspins == 2:
            tag = ('up', 'dn')[isp]
            legend = '{} ({})'.format(label, tag) if label else tag
            if isp == 1:
                col, style = color_dn or 'red', ls_dn
        adapter.line(kp.x, eigen[:, indices] - reference, color=col, ls=style,
                     lw=lw, marker=marker, ms=ms, label=legend)
    if zero_line:
        adapter.axhline(0, ls='dashed', color='gray')
    if set_ylabel:
        adapter.set_ylabel('Energy ({})'.format({'ev': 'eV', 'ry': 'Ry', 'au': 'Ha'}.get(bs.unit, bs.unit)))
    if set_xaxis:
        if ksymbols is not None and len(ksymbols) != len(kp.special_x):
            raise ValueError('Symbols {} do not match special positions {}'.format(ksymbols, kp.special_x))
        adapter.set_xlim(kp.x[0], kp.x[-1])
        adapter.set_xticks(kp.special_x, format_ksymbols(ksymbols, adapter.engine))
        adapter.xgrid(kp.special_x)
        for x in split_kpath_breaks(kp.special_x, ksymbols)[0]:
            adapter.axvline(x, color='black', ls='solid')
    return ax


def plot_fatband(ax, bs, kp, apbs, *, spin=0, ref='vbm', scale=1.0, prop_area=False, colors=None):
    """Plot projector weights as markers.

    ``scale`` multiplies the marker diameter in Grace units (six points).
    Diameter is proportional to weight, or area when ``prop_area=True``.
    """
    adapter = wrap_axes(ax)
    colors = DEFAULT_COLORS if colors is None else colors
    reference = get_energy_reference(bs, ref)
    for i, apb in enumerate(apbs):
        atms, prjs, bands = split_apb(apb)
        weights = bs.get_pwav(atms, prjs, bands)[spin]
        energies = bs.get_eigen(bands)[spin] - reference
        sizes = (6 * scale) ** 2 * (weights if prop_area else weights ** 2)
        for ib in range(energies.shape[1]):
            label = '-'.join(apb.split(':')[:2]) if ib == 0 else None
            adapter.scatter(kp.x, energies[:, ib], sizes[:, ib], colors[i % len(colors)], label)
    return ax


def export_fatband_data(bs, apbs, spin=0) -> list[str]:
    """Return legacy pwav.dat lines, including blank group separators."""
    lines = []
    for apb in apbs:
        atms, prjs, bands = split_apb(apb)
        lines.append('#atom-projector-band:{}'.format(apb))
        lines.extend(export_2d_data(bs.get_pwav(atms, prjs, bands)[spin]))
        lines.append('')
    return lines


def plot_bands_compare(ax, items, *, align='vbm', colors=None, ls=None, ksymbols=None, spin=None):
    """Overlay bands aligned independently; the first path determines the ticks."""
    from copy import deepcopy
    unit = None
    colors = ['black'] + DEFAULT_COLORS if colors is None else colors
    end = None
    for i, item in enumerate(items):
        if isinstance(item, BandPathData):
            bs, kp, label = item.bs, item.kpath(), item.source
            symbols = item.ksymbols if ksymbols is None else ksymbols
        else:
            bs, kp, label = item
            symbols = ksymbols
        if unit is None:
            unit = bs.unit
        elif bs.unit != unit:
            bs = deepcopy(bs)
            bs.unit = unit
        if end is None:
            end = kp.x[-1]
        elif abs(kp.x[-1] - end) > abs(end) * .01:
            _logger.warning('Compared k-path lengths differ by more than 1%')
        style = ('solid' if i == 0 else 'dashed') if ls is None else ls[i % len(ls)]
        col = colors[i % len(colors)]
        plot_band(ax, bs, kp, ref=align, color=col, color_dn=col, ls=style,
                  label=label, ksymbols=symbols, set_xaxis=i == 0, zero_line=i == 0, spin=spin)
    wrap_axes(ax).legend()
    return ax


def plot_band_dos(bs, kp, dos, *, engine='plt', ref='vbm', dos_ref=None, aps=(),
                  erange=(-6., 6.), width_ratios=(3, 1), figsize=None, ksymbols=None, spin=None):
    """Plot bands and vertical DOS sharing an energy axis.

    With ``dos_ref=None`` both use the band reference on a common absolute
    energy scale. Use ``dos_ref='efermi'`` for DOS on its own Fermi scale.
    Grace panels use explicit view coordinates to honor ``width_ratios``.
    """
    from copy import deepcopy
    from mushroom.visual.dosplot import plot_dos
    dos = deepcopy(dos)
    dos.unit = bs.unit
    if engine == 'plt':
        raise_no_module(plt, 'matplotlib.pyplot')
        fig, axes = plt.subplots(1, 2, sharey=True, figsize=figsize,
                                gridspec_kw={'width_ratios': width_ratios, 'wspace': 0})
        axes[1].tick_params(labelleft=False)
    elif engine == 'grace':
        from mushroom.visual.graceplot import Plot
        fig, axes = Plot.subplots(1, 2)
        middle = .15 + .8 * width_ratios[0] / sum(width_ratios)
        axes[0].set_view(xmin=.15, xmax=middle)
        axes[1].set_view(xmin=middle, xmax=.95)
        axes[1].y.set_ticklabel(switch='off')
    else:
        raise ValueError('Unknown engine: {}'.format(engine))
    plot_band(axes[0], bs, kp, ref=ref, ksymbols=ksymbols, spin=spin)
    reference = get_energy_reference(bs, ref) if dos_ref is None else dos_ref
    plot_dos(axes[1], dos, ref=reference, aps=aps, orientation='vertical', spin=spin)
    wrap_axes(axes[1]).set_ylabel('')
    for ax in axes:
        wrap_axes(ax).set_ylim(*erange)
    return fig, tuple(axes)


def bandplot(bs: BandStructure, kp: KPathLinearizer,
             ref: Union[str, float] = 'internal', nbands_max: int = -1,
             ksymbols: Iterable[str] = [], label: Union[str, None] = None,
             ax=None, engine: str = 'plt', color: str = 'k',
             set_xaxis: bool = True, set_ylabel: bool = True, **kwargs):
    """Deprecated wrapper for :func:`plot_band`, preserving the legacy signature."""
    warnings.warn('Use plot_band instead of bandplot', DeprecationWarning, stacklevel=2)
    if ax is None:
        if engine == 'plt':
            raise_no_module(plt, 'matplotlib.pyplot')
            _, ax = plt.subplots(figsize=(7, 7))
        elif engine == 'grace':
            from mushroom.visual.graceplot import Plot
            _, ax = Plot.subplots()
        else:
            raise ValueError('Unknown engine: {}'.format(engine))
    return plot_band(ax, bs, kp, ref=None if ref == 'internal' else ref,
                     bands=(0, min(nbands_max, bs.nbands)) if nbands_max > 0 else None,
                     ksymbols=list(ksymbols) or None, color=color, label=label,
                     set_xaxis=set_xaxis, set_ylabel=set_ylabel, **kwargs)


def plot_qp_correction(ax, e_ks, de, occupied, *, fit=None, colors=('blue', 'red'), ms=None):
    """Plot occupied/empty QP shifts and optional separate fitted lines."""
    adapter = wrap_axes(ax)
    e_ks, de, occupied = np.asarray(e_ks), np.asarray(de), np.asarray(occupied, dtype=bool)
    for key, mask, color in [('vb', occupied, colors[0]), ('cb', ~occupied, colors[1])]:
        if not np.any(mask):
            continue
        adapter.scatter(e_ks[mask], de[mask], np.full(mask.sum(), (ms or 6.) ** 2), color, key)
        if fit and fit[key] is not None:
            values = fit[key]
            x = np.array([e_ks[mask].min(), e_ks[mask].max()])
            label = '{}: {:.3g} E {:+.3g}'.format(key, values['slope'], values['intercept'])
            adapter.line(x, values['slope'] * x + values['intercept'], color=color, label=label)
    adapter.axhline(0, color='gray', ls='dashed')
    adapter.axvline(0, color='gray', ls='dashed')
    adapter.set_xlabel('KS energy (eV)')
    adapter.set_ylabel('QP correction (eV)')
    adapter.legend()
    return ax
