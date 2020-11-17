# -*- coding: utf-8 -*-
"""wrapper and help functions for matplotlib.pyplot"""
import matplotlib as mpl
import matplotlib.pyplot as plt

def gracify(transparent: bool = True, dpi: int = 300):
    """setup rcParams to mimic the style of XmGrace"""
    plt.rcParams["font.family"] = "serif"
    plt.rcParams["font.serif"] = "Times New Roman"
    plt.rcParams["font.sans-serif"] = "Helvetica"
    plt.rcParams["font.monospace"] = "Courier"
    plt.rcParams["xtick.direction"] = "in"
    plt.rcParams["ytick.direction"] = "in"
    plt.rcParams["legend.frameon"] = False
    plt.rcParams["legend.fancybox"] = False
    plt.rcParams["savefig.dpi"] = dpi
    #plt.rcParams["figure.figsize"] = (6.4, 4.8)
    plt.rcParams["savefig.transparent"] = transparent
