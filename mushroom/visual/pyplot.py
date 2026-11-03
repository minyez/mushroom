# -*- coding: utf-8 -*-
"""wrapper and help functions for matplotlib.pyplot"""
try:
    import matplotlib as mpl
except ImportError:
    mpl = None

try:
    import matplotlib.pyplot as plt
except ImportError:
    plt = None

from mushroom.core.utils import raise_no_module


__all__ = [
    "rc_gracify", "gracify_style", "COLUMN_WIDTHS", "figsize",
]


def gracify_style(transparent: bool = False, dpi: int = 300, cmap: str = "RdBu", fontsize: float = 16,
               tick_scale: float = 1.5,
               markersize: float = 12,
               legend_frameon: bool = False, legend_fancybox: bool = False):
    """Return a Grace-like style without changing global state.

    Use locally with ``with mpl.rc_context(gracify_style()): ...``.
    """
    raise_no_module(mpl, "matplotlib")
    style = {}
    style["font.family"] = list(dict.fromkeys(["serif",] + mpl.rcParamsDefault["font.family"]))
    style["font.serif"] = list(dict.fromkeys(["Times New Roman",] + mpl.rcParamsDefault["font.serif"]))
    style["font.sans-serif"] = list(dict.fromkeys(["Helvetica",] + mpl.rcParamsDefault["font.sans-serif"]))
    style["font.monospace"] = list(dict.fromkeys(["Courier",] + mpl.rcParamsDefault["font.monospace"]))
    # style['mathtext.fontset'] = 'dejavuserif'
    style['mathtext.fontset'] = 'cm'
    style["xtick.direction"] = "in"
    style["ytick.direction"] = "in"
    style["legend.frameon"] = legend_frameon
    style["legend.fancybox"] = legend_fancybox
    # disable legend transparency
    style["legend.framealpha"] = 1.0
    style["savefig.dpi"] = dpi
    style["savefig.transparent"] = transparent
    style["image.cmap"] = cmap
    style["font.size"] = fontsize
    style["lines.markersize"] = markersize
    style["xtick.major.size"] = mpl.rcParamsDefault["xtick.major.size"] * tick_scale     # major tick size in points
    style["xtick.minor.size"] = mpl.rcParamsDefault["xtick.minor.size"] * tick_scale       # minor tick size in points
    style["xtick.major.width"] = mpl.rcParamsDefault["xtick.major.width"] * tick_scale     # major tick width in points
    style["xtick.minor.width"] = mpl.rcParamsDefault["xtick.minor.width"] * tick_scale     # minor tick width in points
    style["ytick.major.size"] = mpl.rcParamsDefault["ytick.major.size"] * tick_scale     # major tick size in points
    style["ytick.minor.size"] = mpl.rcParamsDefault["ytick.minor.size"] * tick_scale       # minor tick size in points
    style["ytick.major.width"] = mpl.rcParamsDefault["ytick.major.width"] * tick_scale     # major tick width in points
    style["ytick.minor.width"] = mpl.rcParamsDefault["ytick.minor.width"] * tick_scale     # minor tick width in points
    # axis line width are also adjusted to make it consistent
    style["axes.linewidth"] = mpl.rcParamsDefault["axes.linewidth"] * tick_scale
    return style


def rc_gracify(transparent: bool = False, dpi: int = 300, cmap: str = "RdBu", fontsize: float = 16,
               tick_scale: float = 1.5,
               markersize: float = 12,
               legend_frameon: bool = False, legend_fancybox: bool = False):
    """Set global rcParams to the reproducible Grace-like style."""
    raise_no_module(plt, "matplotlib.pyplot")
    plt.rcParams.update(gracify_style(transparent, dpi, cmap, fontsize, tick_scale,
                                    markersize, legend_frameon, legend_fancybox))


COLUMN_WIDTHS = {
    "aps-single": 3.375, "aps-double": 7.0,
    "acs-single": 3.25, "acs-double": 7.0,
    "nature-single": 3.5, "nature-double": 7.2,
}


def figsize(column: str = "aps-single", aspect: float = 0.75, nrows: int = 1) -> tuple[float, float]:
    """Return figure width and height in inches for a journal column."""
    if column not in COLUMN_WIDTHS:
        raise ValueError("Unknown column {!r}; choose from {}".format(column, ", ".join(COLUMN_WIDTHS)))
    width = COLUMN_WIDTHS[column]
    return width, width * aspect * nrows
