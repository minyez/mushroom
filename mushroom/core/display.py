# -*- coding: utf-8 -*-
"""utilities for showing and displaying data"""
from os import get_terminal_size
import numpy as np

ts = get_terminal_size()
term_columns, term_lines = ts.columns, ts.lines
del ts, get_terminal_size

def set_np_linewidth_ratio(ratio: float = 0.75, thres: int = 100):
    """set the array print linewidth to a ratio of terminal columns

    Args:
        ratio (float)
        thres (int)
    """
    if term_columns > thres:
        np.set_printoptions(linewidth=int(term_columns*ratio))

def block_banner(info: str, width: int = 80) -> str:
    """return a three-line block banner with info centered at the second line"""
    n = len(info)
    if n >= width:
        width = n
    slist = ["="*width, one_line_center_banner(info, width, fill=" "), "="*width]
    return "\n".join(slist)

def one_line_center_banner(info: str, width: int = 80, fill: str = "=") -> str:
    """return a string with centered information by fill with ``fill`` on both sides

    newline in info will be replaced by space
    """
    info = info.replace("\n", " ")
    n = len(info)
    # remove two spaces for join
    width = width - 2
    if n >= width:
        return info
    lf = (width-n) // 2
    rf = width - n - lf
    slist = [fill*lf, info, fill*rf]
    return "{} {} {}".format(*slist)

