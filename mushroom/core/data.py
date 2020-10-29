# -*- coding: utf-8 -*-
"""helper function in dealing with data, digits and mathematics"""
import re
from typing import List
import numpy as np

from mushroom.core.ioutils import trim_after
from mushroom.core.logger import create_logger

_logger = create_logger("data")
del create_logger

def conv_estimate_number(s: str, reserved: bool = False) -> float:
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

def get_divisors(n: int) -> List[int]:
    """get all divisors of integer n, including itself and excluding 1

    Args:
        n (int)
    """
    divs = []

    for i in range(2, n + 1):
        if n % i == 0:
            divs.append(i)
    return divs

def get_mutual_primes(n):
    """find all mutual primer of integer n that are smaller than n

    Args:
        n (int)

    Examples:
    >>> get_mutual_primes(10)
    [1, 3, 7, 9]
    >>> get_mutual_primes(15)
    [1, 2, 4, 7, 8, 11, 13, 14]
    """
    mp = [1,]
    for i in range(2, n):
        is_mp = True
        for j in get_divisors(i):
            if n % j == 0:
                is_mp = False
                break
        if is_mp:
            mp.append(i)
    return mp


def closest_frac(decimal: float, maxn=100, thres=None, ret=1):
    """find the closest fraction number of decimal

    Args:
        decimal (float)
        maxn (int)
        thres (float)

    Returns:
        If such fraction is found, depending on ``ret``, returns

            - 1: float, the guessed fraction
            - 2: (int, int), numerator and denominator 
            - 3: (int, int, float), numerator and denominator, error
            - otherwise: string, the guessed fraction

        ValueError is raised if no such fraction is found
    """
    def _select_return(num, denom, error, ret):
        d = {
            1: num / denom,
            2: (num, denom),
            3: (num, denom, error),
            }
        return d.get(ret, "{:d}/{:d}".format(num, denom))

    f = decimal
    int_part = 0
    err = 1.0
    num = 0
    den = 0
    int_part = int(np.floor(f))
    f -= int_part

    if thres is None:
        # 0.9 is added to avoid getting 0.2 (1/5) for 0.1
        thres = 0.1 ** len(str(decimal).strip('0').split('.')[1]) * 0.9

    # return 0 when value is smaller than threshold
    if f <= thres:
        return _select_return(0 + int_part, 1, thres, ret)

    for _de in range(2, maxn):
        fp = float(_de)
        for _nu in get_mutual_primes(_de):
            __v = float(_nu) / fp
            diff = abs(__v - f)
            if diff < thres:
                return _select_return(_nu + int_part * _de, _de, diff, ret)
            if diff < err:
                num = _nu
                den = _de
    raise ValueError

def fraction(s: str) -> float:
    """compute the value of a string of fraction, e.g. '1/2'

    Args:
        s (str)

    Returns:
        float
    """
    assert s.count('/') == 1
    nu, de = s.split('/')
    return float(nu) / float(de)


class Data:
    """Object for storage and extraction of data

    Args:
        x, y, z (array-like) : positional, data columns in order
        datatype (str) : the data type. See datatypes
        label (str)
        comment (str) : extra comment for the data
        error should be parsed by using keywords arguments, supported are
            dx
            dxl (l means lower)
            dy
            dyl
            dz
            dzl

    Class attributes:
        available_types : available data types

    Public attributes:

    Private attributes:

    Public methods:
        get
        get_extra
        export
        export_extra

    Private methods:

    Constants:
        DATATYPES (dict) : available datatypes
            key is the acronym of the data type
            value a list, optional arguments for left-and-right errors
    """
    extra_data = ['dx', 'dxl', 'dy', 'dyl', 'size']
    DATATYPES = {
        'xy': (2, []),
        'bar': (2, []),
        'xyz': (3, []),
        'xysize': (2, ['size']),
        'xydx': (2, ['dx']),
        'xydy': (2, ['dy']),
        'bardy': (2, ['dy']),
        'xydxdx': (2, ['dx', 'dxl']),
        'xydydy': (2, ['dy', 'dyl']),
        'bardydy': (2, ['dy', 'dyl']),
        'xydxdy': (2, ['dx', 'dy']),
        'xydxdxdydy': (2, ['dx', 'dxl', 'dy', 'dyl']),
        }
    available_types = tuple(DATATYPES.keys())

    def __init__(self, *xyz, datatype: str = None, label: str = None, comment: str = None,
                 **extras):
        datatype, self._extra_cols = Data._check_data_type(*xyz, datatype=datatype, **extras)
        if datatype == "xyz":
            self.x, self.y, self.z = xyz
            self.x = np.array(self.x)
            self.y = np.array(self.y)
            self.z = np.array(self.z)
            self._data_cols = ['x', 'y', 'z']
        elif datatype.startswith("bar") or datatype.startswith("xy"):
            self.x, self.y = xyz
            self.x = np.array(self.x)
            self.y = np.array(self.y)
            self._data_cols = ['x', 'y']
        for opt in self._extra_cols:
            self.__setattr__(opt, extras[opt])
        self.label = label
        self.comment = comment
        self.datatype = datatype

    def xmin(self) -> float:
        """get the min value of abscissa 
        """
        return self.x.min()

    def xmax(self) -> float:
        """get the max value of abscissa 
        """
        return self.x.max()

    def max(self) -> float:
        """get the max value among data point

        If the datatype is xyz, the maximal z value will be returned
        Otherwise the maximal y.
        """
        try:
            return self.__getattribute__('z').max()
        except AttributeError:
            return self.__getattribute__('y').max()

    def min(self) -> float:
        """get the min value among data point

        If the datatype is xyz, the minimal z value will be returned
        Otherwise the minimal y.
        """
        try:
            return self.__getattribute__('z').min()
        except AttributeError:
            return self.__getattribute__('y').min()

    def _get(self, data_cols, scale=1.0, transpose=False):
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
        d = np.stack([self.__getattribute__(arg) for arg in data_cols])
        if transpose:
            d = d.transpose()
        return d * scale

    def _export(self, data_cols, form=None, transpose=False, sep=None) -> List[str]:
        """export data/error to a list, each member as a line of string for data

        Default output will be one line for each data type, i.e.

            'x1[sep]y1[sep]z1'
            'x2[sep]y2[sep]z2'
            'x3[sep]y3[sep]z3'
            ...

        Set `transpose` to True will get

            'x1[sep]x2[sep]x3 ...'
            'y1[sep]y2[sep]y3 ...'
            'z1[sep]z2[sep]z3 ...'

        Args:
            transpose (bool)
            sep (str)
            form (formatting string or its list/tuple) : formatting string
                default to use float
                if a str is parsed, this format apply to all data columns
                if Iterable, each form will be parsed respectively.
        """
        slist = []
        # check if format string is valid 
        if form is not None and isinstance(form, (tuple, list)):
            if len(form) != len(data_cols):
                msg = "format string does not conform data columns"
                raise ValueError(msg, form, len(data_cols))

        data_all = self._get(data_cols)
        return export_2d_data(data_all, transpose=transpose, form=form, sep=sep)

    def get_data(self, transpose=False):
        """get all data values

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

    def get_extra(self, transpose=False):
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
        return self._get(self._extra_cols, transpose=transpose)

    def get(self, transpose=False):
        """get all data and extra value

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
        return self._get(self._data_cols + self._extra_cols, transpose=transpose)

    def export_data(self, form=None, transpose=False, sep=None) -> List[str]:
        """Export the data as a list of strings
        
        See get for the meaning of transpose

        Args:
            sep (str)
            form (formatting string or its list/tuple) : formatting string
                if a str is parsed, this format apply to all data columns
                if Iterable, each form will be parsed respectively.
        """
        return self._export(self._data_cols, form=form, transpose=transpose, sep=sep)

    def export_extra(self, form=None, transpose=False, sep=None) -> List[str]:
        """Export extra data as a list of strings

        See get_extra for the meaning of transpose

        Args:
            sep(str)
            form (formatting string or its list/tuple) : formatting string
                if a str is parsed, this format apply to all data columns
                if Iterable, each form will be parsed respectively.
        """
        return self._export(self._extra_cols, form=form, transpose=transpose, sep=sep)

    def export(self, form=None, transpose=False, sep=None) -> List[str]:
        """Export both data and extras as a list of strings
        
        See get_all for the meaning of transpose

        Args:
            sep (str)
            form (formatting string or its list/tuple) : formatting string
                if a str is parsed, this format apply to all data columns
                if Iterable, each form will be parsed respectively.
        """
        return self._export(self._data_cols + self._extra_cols,
                            form=form, transpose=transpose, sep=sep)

    @classmethod
    def _check_data_type(cls, *xyz, datatype=None, **extras):
        """confirm the data type of input. Valid types are declared in Data.DATATYPES
    
        Args:
            *xyz (array-like):
            datatype (str) : data type of . None for automatic detect
            extras for parsing extra data such as error
                d(x,y,z) (float) : error. when the according l exists, it becomes the upper error
                d(x,y,z)l (float) : lower error
                size (float) : size of marker

        Returns:
            str, list
        """
        extra_cols = []
        # check data size
        try:
            np.array(xyz, dtype='float')
        except ValueError:
            raise ValueError("inconsistent size of xyz data")
        nd, ndp = np.array(xyz).shape
        if nd <= 1:
            raise ValueError("no enough parsed data")
        # automatic detect
        if datatype is None:
            t = {2: 'xy', 3: 'xyz'}[nd]
            for dt, (n, ec) in cls.DATATYPES.items():
                if n == nd and dt.startswith(t) and len(ec) == len(extras):
                    _logger.debug("check for datatype %s", dt)
                    edata = [extras.get(required_e, None) for required_e in ec]
                    find_all = all(edata)
                    if find_all:
                        size_consistent = all(map(lambda x: len(x) == ndp, edata))
                        if not size_consistent:
                            raise ValueError("size of extra data are inconsistent with xy")
                        extra_cols = ec
                        _logger.debug("detected datatype %s", dt)
                        return dt, extra_cols
            raise ValueError("cannot determine the datatype")
        # check consistency
        t = datatype.lower()
        if t in cls.available_types:
            required_n, extra_cols = cls.DATATYPES[t]
            if required_n != nd:
                raise ValueError("Inconsistent xyz data and specified datatype ", datatype)
            find_all = all([required_e in extras for required_e in extra_cols])
            if not find_all:
                raise ValueError("Inconsistent extra data and specified datatype ", datatype)
            _logger.debug("confirmed datatype %s", t)
        else:
            raise ValueError("Unsupported datatype", datatype)
        # some error is parsed
        return t, extra_cols

def export_2d_data(data, form: str = None, transpose: bool = False, sep: str = None) -> List[str]:
    """print the 2-dimension data into list of strings

    Args:
        data (2d array): each row has the same format
        form (str or tuple/list): format string of each type of data.
        transpose (bool) : if set True, the same column will be printed as one line
        sep (str)

    """
    slist = []
    if form is None:
        if transpose:
            l = len([x[0] for x in data])
        else:
            l = len(data[0])
        form = ['{:f}',] * l

    if sep is None:
        sep = " "
    if transpose:
        data = np.transpose(data)
    for i, array in enumerate(data):
        if isinstance(form, str):
            s = sep.join([form.format(x) for x in array])
        elif isinstance(form, (list, tuple)):
            if transpose:
                # array = (x1, y1, z1)
                s = sep.join([f.format(x) for f, x in zip(form, array)])
            else:
                # array = (x1, x2, x3)
                s = sep.join([form[i].format(x) for x in array])
        else:
            raise ValueError("invalid format string {:s}".format(form))
        slist.append(s)
    return slist

