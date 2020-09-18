# -*- coding: utf-8 -*-
"""helper function in dealing with data, digits and mathematics"""
import re
import numpy as np

from mushroom._core.ioutils import trim_after
from mushroom._core.logger import create_logger

_logger = create_logger(__name__)
del create_logger

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
        x, y, z (array-like) : positional, data columns in order
        error_both (bool) : if True, the left error will be used also for right error
        label (str)
        comment (str) : extra comment for the data

    Public attributes:

    Private attributes:

    Public methods:
        get
        get_error
        export
        export_error

    Private methods:

    Constants:
        DATATYPES (dict) : available datatypes
            key is the acronym of the data type
            value a list, optional arguments for left-and-right errors
    """
    DATATYPES = {
        'bar': ['dxl', 'dxr'],
        'xy': ['dxl', 'dxr', 'dyl', 'dyr'],
        'xyz': ['dxl', 'dxr', 'dyl', 'dyr', 'dzl', 'dzr'],
        }

    def __init__(self, *xyz, error_both=True,
                 label=None, comment=None,
                 **kwargs):
        data_type = _check_data_type(*xyz, error_both=error_both, **kwargs)
        self._error_cols = Data.DATATYPES.get(data_type, None)
        # TODO use numpy to treat xyz and error data
        if data_type == "bar":
            self.x = xyz[0]
            self._data_cols = ['x',]
        if data_type == "xy":
            self.x, self.y = xyz
            self._data_cols = ['x', 'y']
        if data_type == "xyz":
            self.x, self.y, self.z = xyz
            self._data_cols = ['x', 'y', 'z']
        for opt in self._error_cols:
            if opt in kwargs:
                self.__setattr__(opt, kwargs[opt])
        self.label = label
        self.comment = comment
        self.type = data_type

    def _get(self, data_cols, transpose=False):
        """get all data value

        default as 
                (x1, y1, z1),
                (x2, y2, z2),
                ...

        Args:
            transpose (bool) : if True, the output will be
                x1, x2, x3...
                y1, y2, y3...
                z1, z2, z3...
        """
        d = [self.__getattribute__(arg) for arg in data_cols]
        if not transpose:
            return list(zip(*d))
        return d

    def _export(self, data_cols, form=None, transpose=False, separator=None):
        """export data/error to a list, each member as a line of string for data

        Default output will be one line for each data type, i.e.

        'x1 y1 z1'
        'x2 y2 z2'
        'x3 y3 z3'
        ...

        Set `transpose` to True will get

        'x1 x2 x3 ...'
        'y1 y2 y3 ...'
        'z1 z2 z3 ...'

        Args:
            transpose (bool)
            separator (str)
            form (formatting string or its list/tuple) : formatting string
                if a str is parsed, this format apply to all data columns
                if Iterable, each form will be parsed respectively.
        """
        slist = []
        # check if format string is valid 
        if form is not None and isinstance(form, (tuple, list)):
            if len(form) != len(data_cols):
                msg = "format string does not conform data columns"
                raise ValueError(msg, form, len(data_cols))

        data_all = self._get(data_cols, transpose=transpose)

        if form is None:
            # if no form is specified, get the type from the first data point
            if transpose:
                # data_all = (xs, ys, zs)
                data1 = [x[0] for x in data_all]
            else:
                # data_all = (1, 2, 3...)
                data1 = data_all[0]
            form = [{True: '{:d}'}.get(isinstance(x, int), '{:f}') for x in data1]

        if separator is None:
            separator = " "
        for i, array in enumerate(data_all):
            if isinstance(form, str):
                s = separator.join([form.format(x) for x in array])
            elif isinstance(form, (list, tuple)):
                if transpose:
                    # array = (x1, x2, x3)
                    s = separator.join([form[i].format(x) for x in array])
                else:
                    # array = (x1, y1, z1)
                    s = separator.join([f.format(x) for f, x in zip(form, array)])
            else:
                raise ValueError("invalid format string {:s}".format(form))
            slist.append(s)
        return slist

    def get(self, transpose=False):
        """get all data value

        Default as
            (x1, y1, z1),
            (x2, y2, z2),
            ...

        Args:
            transpose (bool) : if True, the output will be
                x-array,
                y-array,
                ...
        """
        return self._get(self._data_cols, transpose=transpose)

    def get_error(self, transpose=False):
        """get all error value
       
        Default as 
            (xel1, xer1, yel1, yer1, ...),
            (xel2, xer2, yel2, yer2, ...),

        Args:
            transpose (bool) : if True, the output will be
                xel1, xel2, xel3, ...
                xer1, xer2, xer3, ...
                yel1, yel2, yel3, ...
                ...
        """
        return self._get(self._error_cols, transpose=transpose)

    def get_all(self, transpose=False):
        """get all data and error value

        Default as
                (x1, y1, z1, xel1, xer1, yel1, yer1, ...),
                (x2, y2, z2, xel2, xer2, yel2, yer2, ...),

        Args:
            transpose (bool) : if True, the output will be
                x1, x2, x3, ...
                y1, y2, y3, ...
                ...
                xel1, xel2, xel3, ...
                ...
        """
        return self._get(self._data_cols + self._error_cols, transpose=transpose)

    def export(self, form=None, transpose=False, separator=None):
        """Export the data as a list of strings
        
        See get for the meaning of transpose

        Args:
            separator (str)
            form (formatting string or its list/tuple) : formatting string
                if a str is parsed, this format apply to all data columns
                if Iterable, each form will be parsed respectively.
        """
        return self._export(self._data_cols, form=form, transpose=transpose, separator=separator)

    def export_error(self, form=None, transpose=False, separator=None):
        """Export the error as a list of strings

        See get_error for the meaning of transpose

        Args:
            separator (str)
            form (formatting string or its list/tuple) : formatting string
                if a str is parsed, this format apply to all data columns
                if Iterable, each form will be parsed respectively.
        """
        return self._export(self._error_cols, form=form, transpose=transpose, separator=separator)

    def export_all(self, form=None, transpose=False, separator=None):
        """Export both data and error as a list of strings
        
        See get_all for the meaning of transpose

        Args:
            separator (str)
            form (formatting string or its list/tuple) : formatting string
                if a str is parsed, this format apply to all data columns
                if Iterable, each form will be parsed respectively.
        """
        return self._export(self._data_cols + self._error_cols,
                            form=form, transpose=transpose, separator=separator)


def _check_data_type(*xyz,
                     error_both=True,
                     dxl=None, dxr=None,
                     dyl=None, dyr=None,
                     dzl=None, dzr=None):
    """confirm the data type of input. Valid types are declared in Data.DATATYPES

    Args:
        *xyz (array-like):
        error_both (bool)
    """
    if not xyz:
        raise ValueError("no parsed data")
    t = {1: 'bar', 2: 'xy', 3: 'xyz'}[len(xyz)]
    # some error is parsed
    if any((dxl, dxr, dyl, dyr, dzl, dzr)):
        raise NotImplementedError("currently error is not supported")
    if error_both:
        pass
    return t

