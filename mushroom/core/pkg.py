# -*- coding: utf-8 -*-
"""utilies to detect the file package of which a particular file is used to"""
import pathlib
from io import TextIOWrapper
from os import PathLike
from os.path import splitext, basename
from re import match
from typing import Union
from mushroom.core.ioutils import get_file_ext, grep
from mushroom.core.logger import loggers

__all__ = ["detect", "package_names"]

_logger = loggers["pkg"]

# package-specific tokens and corresponding name of the packages
package_names = {
    "vasp": "VASP",
    "w2k": "WIEN2k",
    "gpaw": "GPAW",
    "abacus": "ABACUS",
    "abi": "ABINIT",
    "aims": "FHI-aims",
    "qe": "Quantum ESPRESSO",
    "bgw": "BerkeleyGW",
    "cp2k": "CP2k",
}


def detect(path: Union[str, PathLike], fail_with_ext: bool = False) -> str:
    """detect the package of a file at `path`

    Args:
        path (str or os.PathLike): path to the file
        fail_with_ext (bool): if set True, extension name will be returned if no package is detected
    """
    fail = {True: get_file_ext(path)}.get(fail_with_ext, None)
    for func in [detect_matchfn, detect_matchhead, detect_matchtail]:
        pkg = func(path)
        if pkg is not None:
            return pkg
    return fail


_package_specific_prefix = {
    r"aims.out": "aims",
}
_package_specific_exts = {
    "POSCAR": "vasp",
    "gpw": "gpaw",
    "struct": "w2k",
}
_package_specific_exts.update(dict((k, k) for k in package_names))
_package_specific_fullnames = {
    "POSCAR": "vasp",
    "CONTCAR": "vasp",
    "INCAR": "vasp",
    "POTCAR": "vasp",
    "KPOINTS": "vasp",
    "pw.in": "qe",
    "ph.in": "qe",
    "geometry.in": "aims",
    "control.in": "aims",
    "STRU": "abacus",
}

# check consistency
for v in _package_specific_prefix.values():
    if v not in package_names:
        raise ValueError(f"invalid pkg name in prefix match: {v}")
for v in _package_specific_fullnames.values():
    if v not in package_names:
        raise ValueError(f"invalid pkg name in fullname match: {v}")
for v in _package_specific_exts.values():
    if v not in package_names:
        raise ValueError(f"invalid pkg name in extension match: {v}")


def detect_matchfn(path: Union[str, PathLike, TextIOWrapper], fail_with_ext: bool = False) -> str:
    """detect the package of a file at `path` by matching its file name

    It matches in the order of full name, prefix and extension name

    Args:
        path (str or os.PathLike): path to the file
        fail_with_ext (bool): if set True, extension name will be returned if no package is detected

    Returns:
        str, the token of package if detected succesfully
        None, if detection fails and fail_with_ext is False
        str, the extension name if detection fails and fail_with_ext is True
        None if path is a directory
    """
    detected_str = "detected by matchfn %r -> %s"
    if isinstance(path, TextIOWrapper):
        path = path.name
    path = pathlib.Path(path)
    fail = {True: get_file_ext(path)}.get(fail_with_ext, None)
    if path.is_dir():
        return None
    full = path.name
    pkg = _package_specific_fullnames.get(full, None)
    if pkg is not None:
        _logger.debug(detected_str, full, pkg)
        return pkg
    # try match the prefix of the filename
    name = basename(path)
    for p, pkg in _package_specific_prefix.items():
        if match(r'^' + p, name) is not None:
            _logger.debug(detected_str, full, pkg)
            return pkg
    name, ext = splitext(full)
    ext = ext[1:]
    pkg = _package_specific_exts.get(ext, None)
    if pkg is not None:
        _logger.debug(detected_str, full, pkg)
        return pkg
    _logger.debug("fail detecting by matchfn %s", full)
    return fail


# key: a tuple, (pattern to match, maxdepth for searching)
#      maxdepth to None to remove the depth limit
_package_specific_head_patterns = {
    (r"&control", 1): "qe",
    (r"^[ ]+Invoking FHI-aims", 2): "aims",
}
_package_specific_tail_patterns = {
    (r"Voluntary context switches", 1): "vasp",
}

# check consistency
for v in _package_specific_head_patterns.values():
    if v not in package_names:
        raise ValueError(f"invalid pkg name in header match: {v}")
for v in _package_specific_tail_patterns.values():
    if v not in package_names:
        raise ValueError(f"invalid pkg name in tail match: {v}")


def detect_matchhead(path: Union[str, PathLike]) -> str:
    """detect the package of a file by matching its head"""
    if isinstance(path, TextIOWrapper):
        path = path.name
    path = pathlib.Path(path)
    if path.is_dir():
        return None
    for (pattern, maxdepth), pkg in _package_specific_head_patterns.items():
        found = grep(pattern, path, maxdepth=maxdepth, from_behind=False)
        if found:
            return pkg
    return None


def detect_matchtail(path: Union[str, PathLike]) -> str:
    """detect the package of a file by matching its tail"""
    if isinstance(path, TextIOWrapper):
        path = path.name
    path = pathlib.Path(path)
    if path.is_dir():
        return None
    for (pattern, maxdepth), pkg in _package_specific_tail_patterns.items():
        found = grep(pattern, path, maxdepth=maxdepth, from_behind=True)
        if found:
            return pkg
    return None
