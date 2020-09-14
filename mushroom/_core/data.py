# -*- coding: utf-8 -*-
"""helper function in dealing with data, digits and mathematics"""
import re
import numpy as np
from mushroom._core.ioutils import trim_after

def conv_estimate_number(s, reserved=True):
    """Convert a string representing a number with error to a float number.

    Args:
        s (str): number string
        reserved (bool): if True, the estimate error is reserved,
            e.g. string like '3.87(6)' will be converted to 3.876.
            Otherwise it will be discarded.

    Retuns:
        float
    """
    if reserved:
        return float(re.sub(r"[\(\)]", "", s))
    return float(trim_after(s, r"\("))


class Data:
    """Object for storage and extraction of data

    Args:
        data_type (str)
        legend (str)
        comment (str)

    Public attributes:

    Private attributes:
        _data_cols : list of name for attributes of data columns
        _options :

    Public methods:
        get_value

    Private methods:

    Constants:
        DATATYPES (dict) : available datatypes
            key is the acronym of the data type
            value a 2-member list, first as positional arguments, usually the data column
            second as optional arguments to parse in
    """
    DATATYPES = {
            'xy': [['x', 'y'], ['precx', 'precy']],
            'xyz': [['x', 'y', 'z'], ['precx', 'precy', 'precz']],
            }

    def __init__(self, data_type='xy', legend=None, comment=None, **kwargs):
        args = Data.DATATYPES.get(data_type, None)
        if args is None:
            raise ValueError(f"Datatype {data_type} is not supported")
        self._data_cols, self._options = args
        for d in self._data_cols:
            if d in kwargs:
                self.__setattr__(d, kwargs[d])
            else:
                raise KeyError(f"{d} should be parsed for datatype {data_type}")
        for opt in self._options:
            if opt in kwargs:
                self.__setattr__(opt, kwargs[opt])
        self.legend = legend
        self.comment = comment
        self.datatype = data_type

    def get_value(self):
        """get all data value"""
        return (self.__getattribute__(arg) for arg in self._data_cols)

