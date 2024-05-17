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

from mushroom.core.ioutils import raise_no_module


__all__ = [
    "rc_gracify",
]


def rc_gracify(transparent: bool = False, dpi: int = 300, cmap: str = "RdBu", fontsize: int = 16,
               tick_scale: float = 1.5):
    """setup rcParams to mimic the style of XmGrace"""
    raise_no_module(plt, "matplotlib")
    plt.rcParams["font.family"] = ["serif",] + plt.rcParams["font.family"]
    plt.rcParams["font.serif"] = ["Times New Roman",] + plt.rcParams["font.serif"]
    plt.rcParams["font.sans-serif"] = ["Helvetica",] + plt.rcParams["font.sans-serif"]
    plt.rcParams["font.monospace"] = ["Courier",] + plt.rcParams["font.monospace"]
    plt.rcParams['mathtext.fontset'] = 'dejavuserif'
    plt.rcParams["xtick.direction"] = "in"
    plt.rcParams["ytick.direction"] = "in"
    plt.rcParams["legend.frameon"] = False
    plt.rcParams["legend.fancybox"] = False
    # disable legend transparency
    plt.rcParams["legend.framealpha"] = 1.0
    plt.rcParams["savefig.dpi"] = dpi
    plt.rcParams["savefig.transparent"] = transparent
    plt.rcParams["image.cmap"] = cmap
    plt.rcParams["font.size"] = fontsize
    plt.rcParams["lines.markersize"] = 12
    plt.rcParams["xtick.major.size"] *= tick_scale     # major tick size in points
    plt.rcParams["xtick.minor.size"] *= tick_scale       # minor tick size in points
    plt.rcParams["xtick.major.width"] *= tick_scale     # major tick width in points
    plt.rcParams["xtick.minor.width"] *= tick_scale     # minor tick width in points
    plt.rcParams["ytick.major.size"] *= tick_scale     # major tick size in points
    plt.rcParams["ytick.minor.size"] *= tick_scale       # minor tick size in points
    plt.rcParams["ytick.major.width"] *= tick_scale     # major tick width in points
    plt.rcParams["ytick.minor.width"] *= tick_scale     # minor tick width in points
    # axis line width are also adjusted to make it consistent
    plt.rcParams["axes.linewidth"] *= tick_scale
