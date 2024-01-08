# -*- coding: utf-8 -*-
"""utilities for showing and displaying data"""
from os import get_terminal_size
import numpy as np

try:
    ts = get_terminal_size()
    term_columns = ts.columns
    # term_lines = ts.lines
    del ts, get_terminal_size
except OSError:
    # get_terminal_size may fail when using pipe
    term_columns = 80


def set_np_linewidth_ratio(ratio: float = 0.75, thres: int = 100):
    """set the array print linewidth to a ratio of terminal columns

    Args:
        ratio (float)
        thres (int)
    """
    if term_columns > thres:
        np.set_printoptions(linewidth=int(term_columns * ratio))
