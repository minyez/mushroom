# -*- coding: utf-8 -*-
"""helper functions for band structure plot"""
from typing import Iterable, Union

from mushroom.core.utils import raise_no_module
from mushroom.core.bs import BandStructure
from mushroom.core.kpoints import KPathLinearizer

try:
    import matplotlib.pyplot as plt
except ImportError:
    plt = None


__all__ = [
]


def bandplot(bs: BandStructure, kp: KPathLinearizer,
             ref: Union[str, float] = "internal",
             nbands_max: int = -1,
             ksymbols: Iterable[str] = [],
             label: Union[str, None] = None,
             ax=None,
             engine: str = "plt",
             color: str = "k",
             set_xaxis: bool = True,
             set_ylabel: bool = True,
             **kwargs):
    """Plot band structure

    Args:
        bs (BandStructure) : band structure to be plotted
        kp (KPathLinearizer) : the 1-D coordinates for the k-points
        ref (string or float) : reference energy, can be "vbm", "cbm", "efermi"
        nbands_max (int)
        ksymbols (iterable of strings) : symbols of special k-points as tick labels of x-axis
        label (str) : label for this band structure as legend
        ax (matplotlib.Axes) : if None, create with current choice of `engine`
        engine (str) : engine for plotting, currently only "plt" (matplotlib, default)
        color (str) : color of bands, parsed to `ax.plot`
        set_xaxis (bool) : whether to set up the x-axis
        set_ylabel (bool) : whether to set up the label of the y-axis (hard coded to "Energy [eV]")

        Other keyword arguments are parsed to `ax.plot` to draw the bands.

    Caveat:
        spin-polarzied band structure is not supported.

    Return:
        The original `ax` is returned if it is not None.
        Otherwise, matplotlib.Axes if `engine` is `matplotlib`.
    """
    if engine == "plt":
        raise_no_module(plt, "matplotlib.pyplot")
    else:
        raise NotImplementedError(
            "engine other than matplotlib not support yet")
    if bs.nspins == 2:
        raise NotImplementedError("spin polarized band plot not support yet")

    ref_value = 0.0
    if isinstance(ref, str):
        if ref == "vbm":
            ref_value = bs.vbm
        elif ref == "efermi":
            ref_value = bs.efermi
        elif ref.startswith("vbm_"):
            # use VBM at first (usually ) point as VBM reference
            ref_value = bs.vbm_sp_kp[0, int(ref.split("_")[1])]
        elif ref == "cbm":
            ref_value = bs.cbm
    else:
        ref_value = ref

    nbands = bs.nbands
    if nbands_max > 0:
        nbands = min(nbands_max, bs.nbands)

    if ax is None:
        if engine == "plt":
            fig, ax = plt.subplots(1, 1, figsize=(7, 7))
        else:
            raise NotImplementedError(
                "engine other than matplotlib not support yet")

    for ib in range(nbands):
        if ib > 0:
            label = None
        ax.plot(kp.x, bs.eigen[0, :, ib] - ref_value,
                label=label, color=color, **kwargs)

    ax.axhline(0.0, ls=":", color="k")
    if set_ylabel:
        ax.set_ylabel("Energy [eV]")
    if set_xaxis:
        ax.xaxis.set_ticks(kp.special_x, labels=ksymbols)
        ax.xaxis.grid(ls="--", color="k")
        ax.set_axisbelow(True)
        ax.set_xlim(kp.x[0], kp.x[-1])

    return ax
