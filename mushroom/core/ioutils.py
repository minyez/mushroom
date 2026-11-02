# -*- coding: utf-8 -*-
# pylint: disable=C0209
"""this module defines some common used utilities for file and string I/O"""
import os
import pathlib
import re
import logging
from contextlib import contextmanager
from io import TextIOWrapper, StringIO
from collections import deque
from itertools import groupby, islice
from difflib import SequenceMatcher
from collections.abc import Iterable, Callable
import sys
from typing import Union, Any, Optional
from collections.abc import Sequence

# make it work as a standalone module
try:
    from mushroom.core.logger import loggers
    create_logger = loggers.__getitem__
except ImportError:
    create_logger = logging.getLogger

lower_greeks = ["alpha", "beta", "gamma", "theta", "omega", "lambda",
                "delta", "zeta", "epsilon"]
upper_greeks = list(x.capitalize() for x in lower_greeks)
greeks = lower_greeks + upper_greeks
greeks_latex = list("\\" + x for x in greeks)

_logger = create_logger("ioutil")
del create_logger


# pylint: disable=R0912,R0914,R0915
def grep(pattern, filename, is_binary: bool = False, error_not_found: bool = False,
         from_behind: bool = False, return_group: Union[bool, int, Sequence[int]] = False,
         maxcounts: Optional[int] = None, maxdepth: Optional[int] = None, return_linenum: bool = False) -> list:
    """emulate command line grep with re package

    Args:
        pattern (str or re.Pattern object): pattern to match in the line
        filename (str, file-like, Iterable of str):
            str: filename to search
            file-like: handle of file
            Iterable: contents of a file from readlines()
        is_binary (bool): read bytes; the regular-expression pattern must also use bytes
        from_behind (bool): search from behind
        error_not_found (bool): raise when no match is found
        maxcounts (int): maximal times of matching
        maxdepth (int): end of line to search
        return_group (bool, int or sequence[int]): False returns full lines; True returns match objects.
            An integer selects a regex group (including group 0), and a sequence selects a tuple of groups.
        return_linenum (bool): return both the matched lines and their indices in the contents

    Returns:
        list or tuple: matched lines, match objects or selected groups according
        to return_group. With return_linenum, also return their zero-based line
        indices in the original input. A missing path returns None unless
        error_not_found is True.
    """
    pattern = re.compile(pattern)
    matched, line_nums = [], []

    def search(lines):
        indexed = enumerate(lines)
        if from_behind:
            # Keep original indices while retaining only the requested tail.
            indexed = reversed(deque(indexed, maxlen=maxdepth))
        elif maxdepth is not None:
            indexed = islice(indexed, maxdepth)
        if maxcounts is not None and maxcounts <= 0:
            return
        for i, line in indexed:
            newline = b"\n" if isinstance(line, bytes) else "\n"
            match = pattern.search(line.rstrip(newline))
            if match is None:
                continue
            line_nums.append(i)
            if return_group is False:
                matched.append(line)
            elif return_group is True:
                matched.append(match)
            elif isinstance(return_group, int):
                matched.append(match.group(return_group))
            else:
                matched.append(tuple(match.group(g) for g in return_group))
            if maxcounts is not None and len(matched) >= maxcounts:
                break

    if isinstance(filename, (str, os.PathLike)):
        filename = pathlib.Path(filename)
        if not filename.is_file():
            if error_not_found:
                raise FileNotFoundError(f"{filename} is not a file")
            return None
        options = {} if is_binary else {"encoding": "utf-8", "errors": "replace"}
        with filename.open("rb" if is_binary else "r", **options) as handle:
            search(handle)
    elif isinstance(filename, (TextIOWrapper, StringIO)):
        search(filename.readlines())
    elif isinstance(filename, Iterable):
        search(filename)
    else:
        raise TypeError(f"expect str, file-like object or Iterable, got {type(filename)}")
    if return_linenum:
        return matched, line_nums
    return matched


def get_dirpath(path):
    """get the absolute path of directory

    Args:
        path (str): the string of the path of file

    Returns:
        str: the absolute path of parent directory, if filepath represents a file,
            otherwise the path of the directory
    """
    p = pathlib.Path(os.path.abspath(path))
    return str(p if p.is_dir() else p.parent)


def get_file_ext(path: Union[str, os.PathLike, TextIOWrapper], greedy: bool = True) -> str:
    """Return the extension name of file at path

    If filePath is a existing directory, None will be returned
    If the path have no characters after "." or have no ".",
    an empty string will be returned.

    Args:
        path (PathLike): the path of the file
        greedy (bool): True returns the final extension (gz for archive.tar.gz);
            False returns everything after the first dot (tar.gz).
    """
    if isinstance(path, TextIOWrapper):
        path = pathlib.Path(path.name)
    path = pathlib.Path(path)
    if path.is_dir():
        return None
    if greedy:
        return path.suffix[1:]
    return path.name.partition(".")[2]


def get_filename_wo_ext(path: Union[str, os.PathLike], dirname=False) -> str:
    """Get the filename without extension

    Args:
        path (str): the path of file
        dirname (bool): keep the directory part of the supplied path

    Symbolic links are not followed. A path without a file name, such as ".",
    is resolved first and the name of that directory is used.
    """
    path = pathlib.Path(path)
    if path.name in ("", ".."):
        path = path.resolve()
    return str(path.with_name(path.stem)) if dirname else path.stem


def get_cwd_name():
    """Get the name of current working directory"""
    return pathlib.Path.cwd().name


def get_matched_files(regex: Optional[str] = None, dirpath=".", relative=False) -> tuple:
    """Get the path of the files whose name matches a regex

    Directories are excluded and only files will be returned.

    Args:
        regex (regex): the regular expression to match the filename.
            If None is parsed, all files will be returned.
        dirpath (str): the directory to search
        relative (bool): if True, the path relative to cwd are returned.
            Otherwise returns the absolute path.

    Returns:
        tuple of strings
    """
    # check the exisitence of path
    fns = []
    cwd = pathlib.Path.cwd()
    dirpath = pathlib.Path(dirpath)
    if not dirpath.is_file():
        for f in dirpath.glob("*"):
            if not f.is_file():
                continue
            if regex is not None:
                if re.search(regex, f.name) is None:
                    continue
            fns.append(f.resolve())
    if relative:
        return tuple(os.path.relpath(f, cwd) for f in fns)
    return tuple(str(f) for f in fns)


def trim_after(string: str, regex: str, include_pattern=False) -> str:
    """Trim a string after the first match of regex.

    If fail to match any pattern, the original string is returned

    The matched pattern is removed unless include_pattern is True.

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


def trim_comment(string: str, comment_regex=r'[\#\!]') -> str:
    """remove comments, starting with # or !"""
    return trim_after(string, comment_regex)


def readlines_remove_comment(filename, comment_regex=r'[\#\!]',
                             keep_empty_lines=True, trim_space=False):
    r"""read lines of a file

    Args:
        filename (path-like, StringIO): input path or readable text stream
        comment_regex (regex): regular expression parsed to ``trim_comment``
        keep_empty_lines (bool): exclude empty lines after comments are trimmed
        trim_space (bool): trim spaces including whitespace, tab, etc

    Returns:
        list, each member being a line without trailing \\n
    """
    lines = []
    tc = "\n"
    if trim_space:
        tc = None
    with open_textio(filename) as h:
        for l in h:
            _l = l.strip(tc)
            _l = trim_after(_l, comment_regex)
            if _l.strip() or keep_empty_lines:
                lines.append(_l)
    return lines


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
            return string[_search.start():]
        return string[_search.end():]
    return string


def trim_both_sides(string: str, regex_left: str, regex_right: str, include_pattern=False) -> str:
    """Trim a string from both sides.

    Basically it first tries to match regex_left, trim the characters on the left
    of the matched pattern, then match regex_right and trim the characters after.

    Args:
        string: string to trim
        regex_left (regex): regular expression marking the left boundary
        regex_right (regex): regular expression marking the right boundary
        include_pattern (bool): if the matched pattern is included
        in the return string
    """
    string = trim_before(string, regex_left, include_pattern=include_pattern)
    return trim_after(string, regex_right, include_pattern=include_pattern)


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
    if not (conv2 in [str, int, float, bool]):
        raise ValueError('conversion type must be str, int, float or bool')
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
                "FALSE": False,
                "F": False,
                ".FALSE.": False,
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


def get_first_last_line(filePath, encoding="utf-8"):
    """return the unstripped first and last lines, or two empty strings for an empty file

    Args:
        filePath (path-like): file to read
        encoding (str): text encoding, default UTF-8

    Returns:
        tuple[str, str]: first and last lines, including their line endings

    Only the two lines are decoded and the file is read backward from its end,
    so a large file or undecodable bytes between the lines are not a problem.
    """
    with open(filePath, "rb") as handle:
        first = handle.readline()
        pos = handle.seek(0, os.SEEK_END)
        tail = b""
        # the newline ending the last line does not count as its start
        while pos > len(first) and b"\n" not in tail[:-1]:
            size = min(4096, pos - len(first))
            pos -= size
            handle.seek(pos)
            tail = handle.read(size) + tail
    last = tail[tail.rfind(b"\n", 0, max(len(tail) - 1, 0)) + 1:] or first
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
        raise ValueError(f'expected Iterable, but got: {type(container)}')
    if not isinstance(string, str):
        raise ValueError(f'expected str, but got: {type(string)}')
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
    if ret:
        return list(dict.fromkeys(ret))
    return ret


def get_prj_indices(prjs, prj):
    """Return the indices of projectors identified by ``prj``.

    A shell name, e.g. "p", selects all orbitals of that shell, e.g. "px", "py" and "pz",
    when the shell itself is not in ``prjs``.

    Args:
        prjs (list or tuple): names of projectors
        prj (int, str, Iterable): the identifier of projectors

    Returns:
        list, unique indices of identified projectors

    Raises:
        ValueError, when no projector is found
    """
    idens = list(prj) if isinstance(prj, Iterable) and not isinstance(prj, str) else [prj,]
    ret = []
    for iden in idens:
        if isinstance(iden, str) and iden in "spdf" and iden not in prjs:
            ret.extend(i for i, name in enumerate(prjs) if name.startswith(iden))
        else:
            ret.extend(get_str_indices_by_iden(prjs, iden))
    if not ret:
        raise ValueError("projector {} is not found in {}".format(prj, list(prjs)))
    return list(dict.fromkeys(ret))


def print_file_or_iowrapper(*s, f=None, mode='w', encoding='utf-8', **kwargs):
    """print string s to file handler f

    Args:
        encoding: encoding used when opening an output path
        *s (str): values forwarded to print
        f (str or TextIOWrapper): the filename or file object where
            the string is exported. If not set, stdout will be used.
        mode (s): only used when s is str
        kwargs: keyword arguments parsed to ``print``
    """
    if isinstance(f, (str, os.PathLike)):
        with open(f, mode=mode, encoding=encoding) as handle:
            print(*s, file=handle, **kwargs)
    else:
        print(*s, file=sys.stdout if f is None else f, **kwargs)
        if isinstance(f, StringIO):
            f.seek(0)


def readtext_split_emptyline(fn):
    """read all text, and split the file string by empty line

    Args:
        fn (PathLike or TextIOWrapper): filepath or a file object which supports readlines

    Returns:
        list of strings
    """
    with open_textio(fn, 'r') as handle:
        return ["".join(lines) for nonempty, lines in groupby(handle, key=lambda line: bool(line.strip()))
                if nonempty]


def cycler(i: int, lt: Union[list, tuple], return_int=False):
    """cycle the index according to the length of list/tuple

    Args:
        return_int: return the wrapped index instead of the selected element
        i (int): index to cycle
        lt (list or tuple): sequence whose elements are cycled
    """
    i = i % len(lt)
    if return_int:
        return i
    return lt[i]


def split_comma(s, convert: Optional[Callable] = None) -> list:
    """split a comma-separated string (without whitespace)

    Args:
        s (str): string to convert
        convert (callable): type to convert.
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


def _decode_num_ends(s: str, t, m_minus=True) -> list:
    """internal function for decode string representing integer/float ends

    Args:
        s (str): string like '8.5:10.2', '-10.2:8', 'm9~'
        t : ``float`` or ``int``
        m_minus (bool): m before the number will be converted to minus.
            useful when parsing range from command line arguments.
            If set False, ValueError will be raised if m is matched

    Returns:
        list, including two floats
    """
    start = None
    end = None
    ends_patterns = {int: re.compile(r"(m)?([+-]?[\d]+)?[:~](m)?([+-]?[\d]+)?"),
                     float: re.compile(r"(m)?([+-]?[.\d]+)?[:~](m)?([+-]?[.\d]+)?")}
    t_strs = {int: "int", float: "float"}
    try:
        t_str = t_strs[t]
        ends_pattern = ends_patterns[t]
    except KeyError as err:
        raise ValueError("Unsupported type for number ends decoding") from err
    matched = ends_pattern.fullmatch(s)
    _logger.debug("decoding %s ends: %s, matched? %r", t_str, s, matched)
    if matched:
        is_start_minus, start, is_end_minus, end = map(matched.group, range(1, 5))
        if not m_minus and (is_start_minus or is_end_minus):
            raise ValueError("m mark is not turned on. Use m_minus=True")
        if start is not None:
            start = t(start) * {None: 1}.get(is_start_minus, -1)
        if end is not None:
            end = t(end) * {None: 1}.get(is_end_minus, -1)
        return start, end
    raise ValueError("invalid {} ends string {}".format(t_str, s))


def decode_int_ends(s: str, m_minus=True) -> list:
    """split and convert a string standing for two ends of an integer range to two numbers

    Args:
        s (str): string like '8:10', '-10:8', 'm9~'
        m_minus (bool): m before the number will be converted to minus.
            useful when parsing range from command line arguments.
            If set False, ValueError will be raised if m is matched

    Returns:
        list, including two integers
    """
    return _decode_num_ends(s, int, m_minus)


def decode_float_ends(s: str, m_minus=True) -> list:
    """split and convert a string standing for two ends of a float range to two numbers

    Args:
        s (str): string like '8.5:10.2', '-10.2:8', 'm9~'
        m_minus (bool): m before the number will be converted to minus.
            useful when parsing range from command line arguments.
            If set False, ValueError will be raised if m is matched

    Returns:
        list, including two floats
    """
    return _decode_num_ends(s, float, m_minus)


def decode_int_range(s: str) -> list:
    """decode a int range of a string into a list of string

    Both endpoints are included.

    Args:
        s (str): string to convert
    """
    int_range = re.compile(r"([\w]+)?([+-]?[\d]+)~([+-]?[\d]+)")
    decoded = []
    m = int_range.fullmatch(s)
    if m:
        prefix, start, end = map(m.group, range(1, 4))
        gen = range(int(start), int(end) + 1)
        if prefix:
            decoded.extend("{:s}{:+d}".format(prefix, i) for i in gen)
        else:
            decoded.extend(list(gen))
    else:
        decoded.append(s)
    return decoded


def get_banner(msg: str, char: str = "#", spacing: int = 4, prefix: Optional[str] = None):
    """get banner string"""
    msg = msg.strip()
    len_msg = len(msg)
    banner_header_footer = char * ((len_msg + spacing * 2) // len(char) + 2)
    banner_msg = char + " " * spacing + msg + " " * spacing + char
    banner_list = [banner_header_footer, banner_msg, banner_header_footer]
    if prefix is None:
        return "\n".join(banner_list)
    return "\n".join(prefix + x for x in banner_list)


def get_similar_str(s: str, slist: list[str]) -> str:
    """get the string in ``slist`` most similar to ``s``"""
    return max(slist, key=lambda x: SequenceMatcher(None, s, x).ratio(), default=None)


def str2bool(s: Any) -> Any:
    """Return a bool type according to input s

    Args:
        s (any type): if s is a string, check if it is one of the following (case insensitive):
            "true", ".true.", "false", ".false."

            If it is the case, a bool type representing it will be returned.

    Returns:
        Any type
    """
    if isinstance(s, str):
        if s.lower() in ["true", ".true."]:
            return True
        if s.lower() in ["false", ".false."]:
            return False
    return s


def bool2str(b: Any, fortran_flavor: bool = False, uppercase: bool = False) -> Any:
    """Return a bool string according to input s

    Args:
        b (any type): if b is a bool, convert to it to a corresponding string and return
        fortran_flavor (bool): surround the logical value with dots
        uppercase (bool): use uppercase logical strings
    Returns:
        Any type
    """
    if isinstance(b, bool):
        if b:
            s = "true"
        else:
            s = "false"
        if uppercase:
            s = s.upper()
        if fortran_flavor:
            s = "." + s + "."
        return s
    return b


@contextmanager
def open_textio(f: Union[str, os.PathLike, StringIO, TextIOWrapper], mode: str = 'r', encoding: str = 'utf-8'):
    """open, and read/write text from a filename(str)/path/TextIOWrapper/StringIO

    Only files opened here are closed on exit. Borrowed streams remain open;
    StringIO objects are rewound for reuse.

    Args:
        f (str, PathLike, TextIOWrapper, StringIO): file-like object to input and output
        mode (str): mode used when opening a path
        encoding (str): encoding used when opening a path
    """
    owned = isinstance(f, (str, os.PathLike))
    if owned:
        f = open(f, mode=mode, encoding=encoding)
    try:
        yield f
    finally:
        if owned:
            f.close()
        elif isinstance(f, StringIO) and not f.closed:
            f.seek(0)


def block_banner(info: str, width: int = 80, fence: str = "=", fill: str = " ") -> str:
    """return a three-line block banner with info centered at the second line"""
    n = len(info)
    if n >= width:
        width = n
    slist = [
        fence * width,
        one_line_center_banner(info, width, fill=fill),
        fence * width
    ]
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
    lf = (width - n) // 2
    rf = width - n - lf
    slist = [fill * lf, info, fill * rf]
    return "{} {} {}".format(*slist)


def conv_integers_to_series(container_int: Union[list[int], tuple[int], set[int]], joint: str = "-") -> list[str]:
    """Convert a list/tuple/set of integers to an integer series.

    Args:
        joint: string joining the inclusive endpoints of each series
        container_int (list/tuple/set of integer): a container of integers.
            Duplicate will be discarded.

    Returns:
        list[str], one string per consecutive series
    """
    if any(not isinstance(x, int) for x in container_int):
        raise ValueError("all members must be integers")
    slist = []
    for _, group in groupby(enumerate(sorted(set(container_int))), key=lambda item: item[1] - item[0]):
        values = [value for _, value in group]
        slist.append(str(values[0]) if len(values) == 1 else joint.join(map(str, (values[0], values[-1]))))
    return slist
