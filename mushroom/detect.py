# -*- coding: utf-8 -*-
"""Detect which code(s) a calculation directory belongs to

Each code is described by a :class:`CodeSignature`, which collects weighted
file patterns and weighted content markers. A code is detected when the sum
of the weights of the matched patterns and markers reaches the threshold.
"""
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Union, Optional
from collections.abc import Sequence

# number of bytes to read from the head of a file when probing its content
PROBE_NBYTES = 16384
# maximal number of files to probe for each marker
PROBE_MAX_FILES = 50
DETECT_THRES = 2


@dataclass
class CodeSignature:
    """signature of the files produced by a code

    Attributes:
        code (str): short name of the code, same as the subcommand of the mushroom CLI
        name (str): full name of the code
        patterns (list): (glob pattern, weight) pairs. A pattern ending with "/" only
            matches directories
        markers (list): (glob pattern, marker, weight) triplets. The marker is searched
            in the head of the files matching the pattern
    """

    code: str
    name: str
    patterns: list[tuple[str, int]] = field(default_factory=list)
    markers: list[tuple[str, str, int]] = field(default_factory=list)


@dataclass
class DetectResult:
    """result of code detection in a directory"""

    code: str
    name: str
    score: int
    evidences: list[str]


SIGNATURES = [
    CodeSignature("aims", "FHI-aims",
                  patterns=[("control.in", 2), ("geometry.in", 2), ("aims.out*", 1)],
                  markers=[("*.out*", "Invoking FHI-aims", 3)]),
    CodeSignature("vasp", "VASP",
                  patterns=[("INCAR", 2), ("POTCAR", 2), ("POSCAR", 1), ("KPOINTS", 1),
                            ("CONTCAR", 1), ("OUTCAR", 1), ("OSZICAR", 1), ("EIGENVAL", 1),
                            ("vasprun.xml", 2)],
                  markers=[("OUTCAR", "vasp.", 2)]),
    CodeSignature("w2k", "WIEN2k",
                  patterns=[("*.struct", 1), ("*.in0", 1), ("*.in1", 1), ("*.in1c", 1),
                            ("*.in2", 1), ("*.in2c", 1), ("*.inm", 1), ("*.klist", 1),
                            ("*.scf", 1), (":log", 1)]),
    CodeSignature("gap", "GAP",
                  patterns=[("gw.inp", 3), ("*.outgw", 2), ("*.eqpeV_GW*", 2)]),
    CodeSignature("librpa", "LibRPA",
                  patterns=[("librpa.out", 3), ("librpa.d/", 2), ("band_out", 1),
                            ("self_energy_omega.dat", 1)]),
    CodeSignature("qe", "Quantum ESPRESSO",
                  patterns=[("*.save/", 2)],
                  markers=[("*.in", "&control", 3), ("*.in", "&CONTROL", 3),
                           ("*.pwi", "&control", 3), ("*.pwi", "&CONTROL", 3),
                           ("*.out", "Program PWSCF", 3)]),
    CodeSignature("abacus", "ABACUS",
                  patterns=[("INPUT", 1), ("STRU", 2), ("KPT", 1), ("OUT.*/", 2)],
                  markers=[("INPUT", "INPUT_PARAMETERS", 2)]),
    CodeSignature("abi", "ABINIT",
                  patterns=[("*.abi", 2), ("*.abo", 2), ("*.files", 1)],
                  markers=[("*.abo", ".Version", 1), ("*.out", "ABINIT", 2)]),
    CodeSignature("yambo", "Yambo",
                  patterns=[("r_setup", 2), ("r-*", 1), ("SAVE/ns.db1", 3)]),
    CodeSignature("w90", "Wannier90",
                  patterns=[("*.win", 2), ("*.wout", 2), ("*_hr.dat", 1), ("*.amn", 1),
                            ("*.mmn", 1)]),
]


def _glob(dirpath: Path, pattern: str) -> list[Path]:
    """glob a pattern in dirpath. A pattern ending with "/" matches directories only"""
    only_dir = pattern.endswith("/")
    matched = dirpath.glob(pattern.rstrip("/"))
    return sorted(p for p in matched if p.is_dir() or not only_dir)


def _has_marker(path: Path, marker: str) -> bool:
    """check if marker is in the head of the file"""
    try:
        with open(path, "rb") as h:
            head = h.read(PROBE_NBYTES)
    except OSError:
        return False
    return marker.encode() in head


def detect_codes(dirpath: Union[str, os.PathLike] = ".",
                 signatures: Optional[Sequence[CodeSignature]] = None,
                 thres: int = DETECT_THRES) -> list[DetectResult]:
    """detect the codes whose calculation files are in dirpath

    Args:
        dirpath (path-like): the directory to check
        signatures (list of CodeSignature): signatures of codes to check against.
            Default to all known signatures
        thres (int): minimal score to detect a code

    Returns:
        list of DetectResult, sorted by the score in descending order
    """
    dirpath = Path(dirpath)
    if not dirpath.is_dir():
        raise NotADirectoryError(f"{dirpath} is not a directory")
    if signatures is None:
        signatures = SIGNATURES

    results = []
    for sig in signatures:
        score = 0
        evidences = []
        for pattern, weight in sig.patterns:
            matched = _glob(dirpath, pattern)
            if matched:
                score += weight
                evidences.extend(p.name + ("/" if p.is_dir() else "") for p in matched)
        for pattern, marker, weight in sig.markers:
            files = [p for p in _glob(dirpath, pattern) if p.is_file()][:PROBE_MAX_FILES]
            hits = [p for p in files if _has_marker(p, marker)]
            if hits:
                score += weight
                evidences.extend(f"{p.name} [{marker}]" for p in hits)
        if score >= thres:
            # remove duplicate evidences while keeping order
            results.append(DetectResult(sig.code, sig.name, score, list(dict.fromkeys(evidences))))
    return sorted(results, key=lambda r: r.score, reverse=True)
