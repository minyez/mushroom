# -*- coding: utf-8 -*-
"""utilies to detect the file package of which a particular file is used to"""
import pathlib
from os import PathLike
from os.path import splitext
from typing import Union
from mushroom.core.ioutils import get_file_ext, grep
from mushroom.core.logger import create_logger

__all__ = ["detect", "package_names"]
_logger = create_logger("pkg")
del create_logger

# package-specific tokens and corresponding name of the packages
package_names = {
    "vasp": "VASP",
    "w2k": "WIEN2k",
    "gpaw": "GPAW",
    "abi": "ABINIT",
    "aims": "FHI-aims",
    "qe": "Quantum Espresso",
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
    }

# check consistency
for v in _package_specific_fullnames.values():
    if v not in package_names:
        raise ValueError("invalid pkg name in fullname match: {}".format(v))
for v in _package_specific_exts.values():
    if v not in package_names:
        raise ValueError("invalid pkg name in extension match: {}".format(v))

def detect_matchfn(path: Union[str, PathLike], fail_with_ext: bool = False) -> str:
    """detect the package of a file at `path` by matching its file name

    It matches in the order of full name, extension name

    Args:
        path (str or os.PathLike): path to the file
        fail_with_ext (bool): if set True, extension name will be returned if no package is detected

    Returns:
        str, the token of package if detected succesfully
        None, if detection fails and fail_with_ext is False
        str, the extension name if detection fails and fail_with_ext is True
        None if path is a directory
    """
    fail = {True: get_file_ext(path)}.get(fail_with_ext, None)
    path = pathlib.Path(path)
    if path.is_dir():
        return None
    full = path.name
    name, ext = splitext(full)
    ext = ext[1:]
    pkg_from_full = _package_specific_fullnames.get(full, None)
    pkg_from_ext = _package_specific_exts.get(ext, None)
    for pkg in [pkg_from_full, pkg_from_ext]:
        if pkg is not None:
            _logger.debug("detected by matchfn (%s, %s) %s", name, ext, pkg)
            return pkg
    _logger.debug("fail detecting by matchfn %s (%s, %s)", full, name, ext)
    return fail

_package_specific_head_patterns = {
    }
_package_specific_tail_patterns = {
    }
# check consistency
for v in _package_specific_head_patterns.values():
    if v not in package_names:
        raise ValueError("invalid pkg name in header match: {}".format(v))
for v in _package_specific_tail_patterns.values():
    if v not in package_names:
        raise ValueError("invalid pkg name in tail match: {}".format(v))

def detect_matchhead(path: Union[str, PathLike]) -> str:
    """detect the package of a file by matching its head"""
    path = pathlib.Path(path)
    if path.is_dir():
        return None
    for pattern, pkg in _package_specific_head_patterns.items():
        found = grep(pattern, path, maxcounts=1, from_behind=False)
        if found:
            return pkg
    return None

def detect_matchtail(path: Union[str, PathLike]) -> str:
    """detect the package of a file by matching its tail"""
    path = pathlib.Path(path)
    if path.is_dir():
        return None
    for pattern, pkg in _package_specific_tail_patterns.items():
        found = grep(pattern, path, maxcounts=1, from_behind=True)
        if found:
            return pkg
    return None

