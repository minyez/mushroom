# -*- coding: utf-8 -*-
"""helper function in dealing with digits and mathematics"""
import re
from mushroom._core.ioutils import trim_after

def conv_estimate_number(s, reserved=True):
    """Convert a string representing a number with error to a float number.

    Literally, string like '3.87(6)' will be converted to 3.876.

    Args:
        s (str): number string
        reserved (bool): if True, the estimate error is reserved

    Retuns:
        float
    """
    if reserved:
        return float(re.sub(r"[\(\)]", "", s))
    return float(trim_after(s, r"\("))

