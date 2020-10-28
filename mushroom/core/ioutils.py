# -*- coding: utf-8 -*-
"""this module defines some common used utilities"""
import os
import re
from io import TextIOWrapper, StringIO
from collections import OrderedDict
from collections.abc import Iterable, Callable
from sys import stdout
from typing import List

from mushroom.core.logger import create_logger

lower_greeks = ["alpha", "beta", "gamma", "theta", "omega"]
upper_greeks = list(x.capitalize() for x in lower_greeks)
greeks = lower_greeks + upper_greeks
greeks_latex = list("\\" + x for x in greeks)

_logger = create_logger("ioutil")
del create_logger


def grep(pattern, filename, is_binary: bool = False, error_not_found: bool = False,
         return_group: bool = False, return_linenum: bool = False) -> List:
    """emulate command line grep with re package

    Args:
        pattern (regex) : pattern to match in the line
        filename (str, file-like, Iterable of str) :
            str: filename to search
            file-like: handle of file
        is_binary (bool)
        error_not_found (bool)
        return_group (bool)
        return_linenum (bool)

    Returns
        one list if return_linenum is False, re.Match object if return_group is True
            otherwise the string of the matched line
        otherwise another list of integers will be returned as well
    """
    if isinstance(filename, str):
        if not os.path.isfile(filename):
            if error_not_found:
                raise FileNotFoundError("{} is not a file".format(filename))
            return None
        mode = 'r' + 'b' * int(is_binary)
        container = open(filename, mode=mode).readlines()
    elif isinstance(filename, (TextIOWrapper, StringIO)):
        container = filename.readlines()
    elif isinstance(filename, Iterable):
        container = filename
    else:
        raise TypeError("expect str, file-like object or Iterable, got", type(filename))

    line_nums = []
    matched = []
    for i, l in enumerate(container):
        print(l)
        m = re.search(pattern, l)
        if m is not None:
            line_nums.append(i)
            matched.append({True: m, False: l}[return_group])
    if isinstance(filename, str):
        container.close()

    if matched == []:
        return None
    if return_linenum:
        return matched, line_nums
    return matched


def get_dirpath(filePath):
    """get the name of directory with filePath

    Args:
        filePath (str): the string of the path of file

    Returns:
        str: the absolute path of parent directory, if filepath represents a file,
            otherwise the path of the directory
    """

    _path = os.path.abspath(filePath)
    if os.path.isdir(_path):
        _path = _path + "/"
    return os.path.dirname(_path)


def get_file_ext(path: str) -> str:
    """Return the extension name of file at path

    If filePath is a existing directory, None will be returned
    If the path have no characters after "." or have no ".", 
    an empty string will be returned.

    Args:
        path (str): the path of the file
    """
    if os.path.isdir(path):
        return None
    base = os.path.basename(os.path.abspath(path))
    return os.path.splitext(base)[1][1:]


def get_filename_wo_ext(path: str) -> str:
    """Get the filename without extension

    Args:
        path (str): the path of file
    """
    fn = os.path.basename(os.path.abspath(path))
    return os.path.splitext(fn)[0]


def get_cwd_name():
    """Get the name of current working directory
    """
    return os.path.basename(os.getcwd())


def get_matched_files(dir_path=".", regex=None) -> tuple:
    """Get the abspath of the files whose name matches a regex

    Only files will be returned, and directories are excluded.

    Args:
        dirPath (str): the directory to search
        regex (regex): the regular expression to match the filename

    Returns:
        tuple of strings
    """
    # check the exisitence of path
    fns = []
    _abs_dir = os.path.abspath(dir_path)
    if os.path.isdir(_abs_dir):
        for i in os.listdir(_abs_dir):
            if regex is not None:
                if not re.match(regex, i):
                    continue
            _fpath = os.path.join(_abs_dir, i)
            if os.path.isfile(_fpath):
                fns.append(_fpath)
    return tuple(fns)


def trim_after(string: str, regex: str, include_pattern=False) -> str:
    """Trim a string after the first match of regex.

    If fail to match any pattern, the original string is returned

    The matched pattern is trimed as well.

    Args:
        string (str): the string to trim
        regex (regex): the regex to match
        include_pattern (bool): if the matched pattern is included
        in the return string
    """
    _search = re.search(regex, string)
    if _search is not None:
        if include_pattern:
            return string[: _search.end()]
        return string[: _search.start()]
    return string


def trim_comment(string: str) -> str:
    """remove comments, starting with # or !"""
    return trim_after(string, r'[\#\!]')


def trim_before(string: str, regex: str, include_pattern=False) -> str:
    """Trim a string from the beginning to the first match of regex.

    If fail to match any pattern, the original string is returned.

    Args:
        string (str): the string to trim
        regex (regex): the regex to match
        include_pattern (bool): if the matched pattern is included
        in the return string
    """
    _search = re.search(regex, string)
    if _search is not None:
        if include_pattern:
            return string[_search.start() :]
        return string[_search.end() :]
    return string


def trim_both_sides(string: str, regex_left: str, regex_right: str, include_pattern=False) -> str:
    """Trim a string from both sides.

    Basically it first tries to match regex_left, trim the characters on the left
    of the matched pattern, then match regex_right and trim the characters after.

    Args:
        regex_left (regex):
        regex_right (regex):
        include_pattern (bool): if the matched pattern is included
        in the return string
    """
    string = trim_before(string, regex_left, include_pattern=include_pattern)
    return trim_after(string, regex_right, include_pattern=include_pattern)


def check_duplicates_in_tag_tuple(tagtuple) -> int:
    """Check if there is duplicate in a tag tuple, case sensitive

    Args:
        tagTuple (tuple) : the tag tuple to check
    """
    dup = -1
    for i, k in enumerate(tagtuple):
        if k in tagtuple[:i]:
            dup = i
            break
    return dup


# def data_normalization(data, scale=1.0, normByPeak=True):
#     '''Normalize the 1D data.

#     Args:
#         data (iterable): the container of 1D data
#         normByPeak (bool) : when set True, the normalization factor will be
#             the peak absolute value. Otherwise, the sum of absolute values
#             will be used as normalization factor.

#     Returns:
#         numpy array, the normalized data
#     '''
#     import numpy as np
#     assert len(np.shape(data)) == 1
#     assert isinstance(normByPeak, bool)

#     _a = []
#     try:
#         _a = np.array(data, dtype="float64")
#     except ValueError:
#         raise ValueError("the data cannot be converted.")

#     _sum = np.sum(np.abs(_a)) / scale
#     _max = np.max(np.abs(_a)) / scale
#     if normByPeak:
#         return _a / _max
#     return _a / _sum


# def find_data_extreme(data):
#     '''Find the point at which the data reaches extrema

#     Returns:
#         dict, with two keys, "min" and "max".
#         Either key has a 2-member tuple with its first the min/max value
#         and second the coordinate where it reaches the extreme
#     '''
#     pass


def find_vol_dirs(path=".", voldir_pat=None, separator="_", index=1):
    """Find names of directories corresponding to calculation with lattice of different volumes

    Args:
        path (str): the path to search directories within. Default is CWD.
        voldir_pat (regex): the pattern of the names of volume directories
            If not specified, use "V_x.xx" where x is 0-9
        separator (str)
        index (int)

    Returns:
        list of strings
    """
    p = voldir_pat
    if p is None:
        p = r"^V_\d.\d+"
    dirs = []
    for d in os.listdir(path):
        if re.match(p, d):
            dirs.append(d)

    def __sort_vol(voldir_str):
        return float(voldir_str.split(separator)[index])

    dirs = sorted(dirs, key=__sort_vol)
    return dirs


def conv_string(string, conv2, *indices, sep=None, strips=None):
    """Split the string and convert substrings to a specified type.

    Args:
        string (str): the string from which to convert value
        conv2: the type to which the substring will be converted
            support ``str``, ``int``, ``float``, ``bool``
        indices (int): if specified, the substring with indices in the splitted
            string lists will be converted. otherwise, all substring will be converted.
        sep (regex): the separators used to split the string.
        strips (str): extra strings to strip for each substring before conversion

    Returns:
        ``conv2``, or list of ``conv2`` type
    """
    assert conv2 in [str, int, float, bool]
    str_tmp = string.strip()
    if sep is not None:
        str_list = re.split(sep, str_tmp)
    else:
        str_list = str_tmp.split()
    if strips is None:
        str_list = [x.strip() for x in str_list]
    else:
        str_list = [x.strip(" " + strips) for x in str_list]

    # need to convert to float first for converting to integer
    if conv2 is int:
        def convfunc(x):
            return int(float(x))
    elif conv2 is bool:
        def convfunc(x):
            return {
                "TRUE": True,
                "T": True,
                ".TRUE.": True,
                ".T.": True,
                "FALSE": True,
                "F": True,
                ".FALSE.": True,
                ".F.": False,
            }.get(x.upper(), None)
    else:
        convfunc = conv2

    if len(indices) == 0:
        return list(map(convfunc, str_list))
    if len(indices) == 1:
        return convfunc(str_list[indices[0]])
    conv_strs = [str_list[i] for i in indices]
    return list(map(convfunc, conv_strs))


def get_first_last_line(filePath, encoding=stdout.encoding):
    """Return the first and the last lines of file

    The existence of filePath should be check beforehand.

    Args:
        filePath (str): the path of the file
        encoding (str): the encoding of the file. Default stdout.encoding

    Returns
        two strings (unstripped)
    """
    with open(filePath, "rb") as f:
        first = f.readline()  # Read the first line.
        f.seek(-2, os.SEEK_END)  # Jump to the second last byte.
        while f.read(1) != b"\n":  # Until EOL is found...
            # ...jump back the read byte plus one more.
            f.seek(-2, os.SEEK_CUR)
        last = f.readline()  # Read last line.
    # encode string
    return str(first, encoding), str(last, encoding)


def get_str_indices(container, string):
    """Return the indices of ``string`` in a list or tuple``container``

    Args:
        container (Iterable): container of strings
        string (str): the string to locate

    Returns:
        list
    """
    if not isinstance(container, Iterable):
        raise ValueError("expected Iterable, but got", type(container))
    if not isinstance(string, str):
        raise ValueError("expected str, but got", type(string))
    return [i for i, s in enumerate(container) if s == string]


def get_str_indices_by_iden(container, iden=None):
    """Return the indices of identified strings in a list or tuple ``container``.

    The strings are identified by ``iden``, either a str, int, or a Iterable of these types.
    If ``iden`` is int or corresponding Iterable, the value greater or equal to the
    length of ``container`` will be ignored.

    Args:
        container (list or tuple): container of strings
        iden (int, str, Iterable): the identifier for string to locate

    Returns:
        list, unique indices of identified strings
    """
    ret = []
    if iden is None:
        return ret
    l = len(container)
    if isinstance(iden, int):
        if iden < l:
            ret.append(iden)
    elif isinstance(iden, str):
        ret.extend(get_str_indices(container, iden))
    elif isinstance(iden, Iterable):
        for i in iden:
            if isinstance(i, int):
                if i < l:
                    ret.append(i)
            elif isinstance(i, str):
                ret.extend(get_str_indices(container, i))
    if ret != []:
        return list(OrderedDict.fromkeys(ret).keys())
    return ret

def print_file_or_iowrapper(s, f=None, mode='w'):
    """print string s to file handler f
    Args:
        s (str) :
        f (str or TextIOWrapper) : the filename or file object where
            the string is exported. If not set, stdout will be used.
        mode (s) : only used when s is str
    """
    if isinstance(f, str):
        h = open(f, mode)
    if isinstance(f, TextIOWrapper):
        h = f
    if f is None:
        h = stdout
    print(s, file=h)
    if isinstance(f, str):
        h.close()

#class Smearing:
#    """class with different smearing schemes implemented as static method
#    """
#
#    @staticmethod
#    def gaussian(x, x0, sigma):
#        """Gaussian smearing
#        """
#        return (
#            np.exp(-np.subtract(x, x0) ** 2 / sigma ** 2 / 2.0)
#            / sigma
#            / np.sqrt(2.0 * PI)
#        )


def split_comma(s, convert: Callable = None) -> List:
    """"split a comma-separated string (without whitespace)

    Args:
        s (str)
        convert (callable) : type to convert.
            If set, will attempt to convert each splitted string to type `convert`.
            If failed, it will be returned as str.
    """
    container = []
    if convert is None:
        return s.split(',')
    for x in s.split(','):
        try:
            container.append(convert(x))
        except ValueError:
            if convert is int and "~" in x:
                container.extend(decode_int_range(x))
            else:
                container.append(x)
    return container

def decode_float_ends(s: str, m_minus=True) -> List:
    """split and convert a string standing for two ends of a float range to two numbers


    Args:
        s (str) : string like '8.5:10.2', '-10.2:8', 'm9~'
        m_minus (bool) : m before the number will be converted to minus.
            useful when parsing range from command line arguments.
            If set False, ValueError will be raised if m is matched

    Returns:
    """
    start = None
    end = None
    float_ends = re.compile(r"(m)?([+-]?[.\d]+)?~(m)?([+-]?[.\d]+)?")
    matched = float_ends.fullmatch(s)
    if matched:
        is_start_minus, start, is_end_minus, end = map(matched.group, range(1, 5))
        if not m_minus and (is_start_minus or is_start_minus):
            raise ValueError("m mark is not turned on. Use m_minus=True")
        if start is not None:
            start = float(start) * {None: 1.}.get(is_start_minus, -1.)
        if end is not None:
            end = float(end) * {None: 1.}.get(is_end_minus, -1.)
        return start, end
    raise ValueError("invalid float ends string {}".format(s))

def decode_int_range(s: str) -> List:
    """decode a int range of a string into a list of string

    Both endpoints are included.

    Args:
        s (str)
    """
    int_range = re.compile(r"([\w]+)?([+-]?[\d]+)~([+-]?[\d]+)")
    decoded = []
    m = int_range.fullmatch(s)
    if m:
        prefix, start, end = map(m.group, range(1, 4))
        gen = range(int(start), int(end)+1)
        if prefix:
            decoded.extend("{:s}{:+d}".format(prefix, i) for i in gen)
        else:
            decoded.extend(list(gen))
    else:
        decoded.append(s)
    return decoded


def fortran_write(fortran_format: str, *args, file=stdout):
    """write out arguments in a Fortran format (without parentheses)

    Args:
        fortran_format (str)
        file (file-like object)
    """
    python_format = fortran_format
    try:
        print(python_format.format(*args), file=file)
    except ValueError:
        info = "unbalanced Fortran format string ({}) and number of arguments {}".format\
               (fortran_format, len(args))
        raise ValueError(info)
    raise NotImplementedError


def fortran_read(fstring: str, fortran_format: str):
    """read in data according to Fortran format string (without parentheses)

    This emulation is implemented by using ``re``

    Args:
        fstring (str) : string to decode as Fortran
        fortran_format (str): Fortran format string
    
    Returns:
        list
    """
    raise NotImplementedError

