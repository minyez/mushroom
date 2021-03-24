# -*- coding: utf-8 -*-
"""wrapper and help functions for matplotlib.pyplot"""
try:
    import matplotlib as mpl
    import matplotlib.pyplot as plt
except ImportError:
    mpl = None
    plt = None

from mushroom.core.ioutils import raise_no_module

def rc_gracify(transparent: bool = False, dpi: int = 300):
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
    plt.rcParams["savefig.dpi"] = dpi
    plt.rcParams["savefig.transparent"] = transparent
    plt.rcParams["axes.linewidth"] = 1.5
    plt.rcParams["image.cmap"] = "RdBu"
    plt.rcParams["font.size"] = 16
    plt.rcParams["lines.markersize"] = 12
    plt.rcParams["xtick.major.size"] *= 1.5     # major tick size in points
    plt.rcParams["xtick.minor.size"] *= 1.5       # minor tick size in points
    plt.rcParams["xtick.major.width"] *= 1.5     # major tick width in points
    plt.rcParams["xtick.minor.width"] *= 1.5     # minor tick width in points
    plt.rcParams["ytick.major.size"] *= 1.5     # major tick size in points
    plt.rcParams["ytick.minor.size"] *= 1.5       # minor tick size in points
    plt.rcParams["ytick.major.width"] *= 1.5     # major tick width in points
    plt.rcParams["ytick.minor.width"] *= 1.5     # minor tick width in points
