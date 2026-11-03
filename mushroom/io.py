# -*- coding: utf-8 -*-
"""functionality for IO"""
import os
from typing import Union, Optional

import numpy as np

from mushroom.core.pkg import detect
from mushroom.core.logger import loggers
# For CellIO
from mushroom.core.cell import Cell
from mushroom.w2k import Struct

_logger = loggers["io"]

__all__ = [
    "CellIO", "detect_code", "read_band", "read_dos", "read_qp_pair",
]


class CellIO:
    """Read, manipulate and"""

    avail_writers = list(Cell.avail_exporters) + ["w2k", ]
    avail_readers = list(Cell.avail_readers) + ["w2k", ]

    default_writer = "vasp"
    assert default_writer in avail_writers

    def __init__(self, path_cell: str, format=None):
        if format is None:
            format = detect(path_cell, fail_with_ext=True)
        if format not in self.avail_readers:
            raise ValueError("unsupported format for reading cell: {}".format(format))

        if format == "w2k":
            c = None
            s = Struct.read(path_cell)
        else:
            c = Cell.read(path_cell, format=format)
            s = None
        _logger.info("Reading %r with format %s", path_cell, format)

        self._format_read = format
        self._cell: Cell = c
        self._struct: Struct = s

    def manipulate(self, primitize=False, standardize=False, no_idealize=False, supercell=None,
                   **kwargs) -> Union[None, list[int]]:
        """manipulate the read cell"""
        if self._format_read == "w2k":
            if primitize or standardize:
                raise NotImplementedError("primitive w2k format is not supported")
        retval = None
        if standardize:
            self._cell = self._cell.standardize(to_primitive=primitize, no_idealize=no_idealize)
        else:
            if primitize:
                self._cell = self._cell.primitize()
        if supercell:
            retval: list[int]
            self._cell, retval = self._cell.get_supercell(*supercell, **kwargs)
        return retval

    def write(self, output_path: Optional[Union[str, os.PathLike]] = None, format: Optional[str] = None, coord_system: str = "D") -> None:
        """write the cell to ``output_path`` in the format of program ``format``

        Args:
            output_path (path-like): output structure path, or None to print to stdout
            format (str): identifier for program
            coord_system (str): direct or cartesian, except for wien2k
        """
        if format is None:
            if output_path is None:
                format = self._format_read
                _logger.debug("output not specfied, using same format as read: %s", format)
            else:
                format = detect(output_path)
            if not format:
                format = self.default_writer
                _logger.debug("fail to detect a format for writing cell, use default writer: %s",
                              format)

        _logger.info("Writing to %r with format %s", output_path, format)

        if self._format_read == "w2k":
            if format == "w2k":
                self._struct.write(filename=output_path)
            else:
                c = self._struct.get_cell()
                with c.temporary_representation(coord_sys=coord_system):
                    c.write(format, filename=output_path)
            return

        # writer for a non-wien2k read-in cell
        if format == "w2k":
            Struct.from_cell(self._cell).write(filename=output_path)
        else:
            with self._cell.temporary_representation(coord_sys=coord_system):
                self._cell.write(format, filename=output_path)


def read_elsi_to_csc(fn, verbose=False):
    """Read ELSI CSC file format.

    Adapted from the same function in FHI-aims utitlities

    Args:
        fn (str): path to the ELSI CSC file
        verbose (bool): verbositiy control

    Returns:
        scipy sparse matrix
    """
    # Keep scipy optional at module import time.
    import scipy.sparse as sp

    with open(fn, "rb") as handle:
        data = handle.read()
    header = np.frombuffer(data, dtype="<i8", count=16)
    n_basis, nnz = int(header[3]), int(header[5])
    if verbose:
        _logger.info("ELSI header: %s", header)
        _logger.info("Reading %s matrix", "complex" if header[2] else "real")
    offset = 128
    col_ptr = np.append(np.frombuffer(data, dtype="<i8", count=n_basis, offset=offset), nnz + 1) - 1
    offset += n_basis * 8
    row_idx = np.frombuffer(data, dtype="<i4", count=nnz, offset=offset) - 1
    offset += nnz * 4
    dtype = "<c16" if header[2] else "<f8"
    # CSC values are writable, matching the former array constructor.
    values = np.frombuffer(data, dtype=dtype, count=nnz, offset=offset).copy()
    return sp.csc_matrix((values, row_idx, col_ptr), shape=(n_basis, n_basis))


def detect_code(path, code=None):
    """Identify a native calculation from its filename or directory signatures.

    Args:
        path (path-like): Native output file or calculation directory.
        code (str or None): Explicit program identifier; when supplied, return
            its lowercase form without inspecting the path.

    Returns:
        str: Program identifier, such as vasp, aims, w2k, librpa or gap.

    Raises:
        ValueError: If detection fails or the highest directory scores are tied.
    """
    from pathlib import Path

    from mushroom.detect import detect_codes
    path = Path(path)
    if code is not None:
        return code.lower()
    if path.is_dir():
        results = detect_codes(path)
        if results:
            codes = [r.code for r in results if r.score == results[0].score]
            if len(codes) == 1:
                return codes[0]
            raise ValueError("Ambiguous programs: {}; specify code=".format(", ".join(codes)))
    else:
        name = path.name
        if name.startswith(("EIGENVAL", "PROCAR", "DOSCAR", "OUTCAR")):
            return "vasp"
        if "band" in name and name.endswith(".out") or name.endswith("aims.out"):
            return "aims"
        if ".energy" in name or ".dos" in name or name.endswith(".scf"):
            return "w2k"
        if name == "librpa.out":
            return "librpa"
        if ".eqpeV" in name:
            return "gap"
    raise ValueError("Cannot infer program for {}; specify code=".format(path))


def read_band(path, code: Optional[str] = None, kind: str = "ks",
              projections: bool = False, **kwargs):
    """Read band data and a path from native output or a NumPy archive.

    Program readers are imported when needed; no plotting or CLI dependency
    is required. Archives contain NumPy arrays and JSON metadata without pickle.

    Args:
        path (path-like): Native file, calculation directory or BandPathData npz.
        code (str or None): Program identifier; None uses detect_code.
        kind (str): Energy kind: ks, gw, qp or exx as supported by the reader.
        projections (bool): Request projector weights (VASP PROCAR or aims Mulliken).
        **kwargs: Native reader options, including casename for WIEN2k. unit
            selects the returned energy unit. efermi is in the native energy unit:
            aims shifts printed energies and retains printed occupations; other
            readers reset occupations at this threshold. Archives load as saved.

    Returns:
        BandPathData: Energies shaped (nspins, nkpts, nbands), fractional kpts
        shaped (nkpts, 3), and optional reciprocal vectors shaped (3, 3) as rows
        in inverse Angstrom including 2pi.

    Raises:
        ValueError: If detection is ambiguous, kind is invalid, or archive metadata
            is incompatible.
        FileNotFoundError: If required native files are absent.
        NotImplementedError: If the program has no band reader.
    """
    from pathlib import Path

    from mushroom.core.bs import BandPathData
    path = Path(path)
    if path.suffix == ".npz":
        return BandPathData.load(path)
    code = detect_code(path, code)
    directory = path if path.is_dir() else path.parent
    recp = symbols = None
    source = []
    unit = kwargs.pop("unit", None)
    efermi = kwargs.pop("efermi", None)
    cell = None
    if code == "vasp":
        from mushroom.vasp import read_eigen, read_procar, read_kpath_symbols
        if kind != "ks":
            raise ValueError("vasp band supports kind='ks' only")
        projections = projections or (not path.is_dir() and path.name.startswith("PROCAR"))
        filename = directory / ("PROCAR" if projections else "EIGENVAL") if path.is_dir() else path
        if projections and not path.is_dir() and not path.name.startswith("PROCAR"):
            filename = directory / "PROCAR"
        if projections:
            bs, kpts = read_procar(filename, **kwargs)
        else:
            bs, _, kpts = read_eigen(filename, **kwargs)
        source.append(filename)
        for name in ("POSCAR", "CONTCAR"):
            if (directory / name).is_file():
                cell = Cell.read_vasp(directory / name)
                source.append(directory / name)
                if projections:
                    bs.atms = cell.atms
                break
        if (directory / "KPOINTS").is_file():
            symbols = read_kpath_symbols(directory / "KPOINTS")
            source.append(directory / "KPOINTS")
    elif code == "aims":
        from mushroom.aims.band import read_band_output, read_band_mulliken_output
        from mushroom.aims.input import Control, get_path_ksymbols
        if kind not in ("ks", "gw"):
            raise ValueError("aims band supports kind='ks' or 'gw'")
        projections = projections or (not path.is_dir() and "bandmlk" in path.name)
        prefix = "bandmlk" if projections else ("GW_band" if kind == "gw" else "band")
        files = sorted(directory.glob(prefix + "1*.out")) if path.is_dir() else [path]
        down = sorted(directory.glob(prefix + "2*.out")) if path.is_dir() else []
        if not path.is_dir() and prefix + "1" in path.name:
            other = path.with_name(path.name.replace(prefix + "1", prefix + "2", 1))
            if other.is_file():
                down = [other]
        if not files:
            raise FileNotFoundError("No {}1*.out in {}".format(prefix, directory))
        reader = read_band_mulliken_output if projections else read_band_output
        bs, kpts = reader(*files, bfiles_spin=down or None, efermi=efermi, **kwargs)
        source.extend(files + down)
        if (directory / "control.in").is_file():
            symbols = get_path_ksymbols(Control.read(directory / "control.in").get_output("band", []))
            symbols = [s.lstrip("\\") if s else "" for s in symbols] or None
            source.append(directory / "control.in")
    elif code == "w2k":
        from mushroom.w2k import read_band_path
        if kind != "ks":
            raise ValueError("w2k band supports kind='ks' only")
        casename = kwargs.pop("casename", None)
        if casename is None and not path.is_dir():
            casename = path.name.split(".energy")[0]
        result = read_band_path(directory, casename=casename, energyfile=None if path.is_dir() else path,
                                efermi=efermi, **kwargs)
        if efermi is not None:
            result.bs.reset_occupations(efermi=efermi, unit=result.bs.unit)
        if unit is not None:
            result.bs.unit = unit
        return result
    elif code == "librpa":
        from mushroom.librpa import read_quasi_particle_energies_stdout
        filename = directory / "librpa.out" if path.is_dir() else path
        bs, kpts = read_quasi_particle_energies_stdout(filename, kind=kind, **kwargs)
        # The native reader repeats coordinates for each spin channel.
        kpts = kpts[:bs.nkpts]
        source.append(filename)
    else:
        raise NotImplementedError("Supported band programs: vasp, aims, w2k, librpa; got " + code)
    if code in ("aims", "librpa") and (directory / "geometry.in").is_file():
        cell = Cell.read_aims(directory / "geometry.in")
        source.append(directory / "geometry.in")
    if cell is not None:
        cell.unit = "ang"
        recp = cell.b
    if efermi is not None and code != "aims":
        bs.reset_occupations(efermi=efermi, unit=bs.unit)
    if unit is not None:
        bs.unit = unit
    return BandPathData(bs, np.asarray(kpts), recp, symbols, code, ";".join(map(str, source)))


def _w2k_dos_files(directory, casename):
    """Select one case's non-spin eV DOS files in numeric channel order."""
    import re
    from pathlib import Path

    directory = Path(directory)
    pattern = re.compile(re.escape(casename) + r"\.dos(\d+)ev")
    files = []
    spin_files = False
    for path in directory.iterdir():
        if not path.is_file():
            continue
        match = pattern.fullmatch(path.name)
        if match:
            files.append((int(match.group(1)), path))
        elif re.fullmatch(re.escape(casename) + r"\.dos\d+ev(?:up|dn)", path.name):
            spin_files = True
    if files:
        return [path for _, path in sorted(files)]
    if spin_files:
        raise NotImplementedError("Spin-resolved WIEN2k DOS requires explicit file paths; "
                                  "specify one spin channel by file path")
    raise FileNotFoundError("No {}.dos{{n}}ev files in {}".format(casename, directory))


def read_dos(path, code: Optional[str] = None, sigma: float = 0.05, **kwargs):
    """Read a DOS archive/output or broaden eigenvalues into a DOS.

    Args:
        path (path-like): Native file, calculation directory or DensityOfStates npz.
            WIEN2k directories select only case.dos{n}ev in numeric order.
        code (str or None): Program identifier; None uses detect_code.
        sigma (float): Gaussian broadening width in the band reader's energy unit
            (eV by default); used only when generating DOS from bands.
        **kwargs: Options passed to the native DOS or band reader, including
            casename for WIEN2k. Archives load as saved.

    Returns:
        DensityOfStates: Energy grid (nedos,), total DOS (nspins, nedos), and
        optional projected DOS (nspins, nedos, natms, nprjs). DOS is per energy
        unit of the returned object.

    Raises:
        ValueError: If program detection or archive metadata is invalid.
        FileNotFoundError: If required files or non-spin eV DOS files are absent.
        NotImplementedError: If a WIEN2k directory contains only spin DOS files;
            supply an explicit file path for one channel.
    """
    from pathlib import Path

    from mushroom.core.dos import DensityOfStates
    path = Path(path)
    if path.suffix == ".npz":
        return DensityOfStates.load(path)
    code = detect_code(path, code)
    directory = path if path.is_dir() else path.parent
    if code == "vasp":
        from mushroom.vasp import read_doscar
        dos = read_doscar(directory / "DOSCAR" if path.is_dir() else path, **kwargs)
        if dos.has_pdos() and (directory / "POSCAR").is_file():
            atms = Cell.read_vasp(directory / "POSCAR").atms
            if len(atms) == dos.natms:
                dos.atms = atms
            else:
                _logger.warning("POSCAR atom count differs from DOSCAR; retaining numeric atom labels")
        return dos
    if code == "w2k":
        from mushroom.w2k import read_dos as read_w2k_dos, get_inputs
        casename = kwargs.pop("casename", None)
        structfile = Path(get_inputs("struct", dirpath=directory, casename=casename)[0])
        struct = Struct.read(structfile)
        files = _w2k_dos_files(directory, structfile.stem) if path.is_dir() else [path]
        dos = read_w2k_dos(*files, mults=struct.mults, **kwargs)
        if dos.has_pdos():
            dos.atms = [x[:2].strip() for x in struct.atms_types]
        return dos
    _logger.info("DOS generated by broadening eigenvalues with sigma=%s", sigma)
    return read_band(path, code=code, **kwargs).bs.get_dos(sigma=sigma)


def read_qp_pair(path, code: Optional[str] = None):
    """Read KS and QP energies from the same printed band window.

    Args:
        path (path-like): Native output file or calculation directory.
        code (str or None): aims, librpa, gap or vasp; None uses detect_code.

    Returns:
        tuple of BandStructure: KS and QP objects with energies shaped
        (nspins, nkpts, nbands), both starting at the same band. Each object's
        unit describes its energies; qp_correction converts them to eV.

    Raises:
        ValueError: If detection is ambiguous or a GAP directory has multiple
            eqpeV files (or none).
        FileNotFoundError: If the requested native output is absent.
        NotImplementedError: If the program has no QP pair reader.
    """
    from pathlib import Path
    path = Path(path)
    code = detect_code(path, code)
    if code == "aims":
        from mushroom.aims.stdout import StdOut
        output = StdOut(path / "aims.out" if path.is_dir() else path)
        return output.get_QP_bandstructure("eps")[0], output.get_QP_bandstructure("qp")[0]
    if code == "librpa":
        from mushroom.librpa import read_quasi_particle_energies_stdout as read
        filename = path / "librpa.out" if path.is_dir() else path
        return read(filename, kind="ks")[0], read(filename, kind="qp")[0]
    if code == "gap":
        from mushroom.gap import Eqpev
        files = sorted(path.glob("*.eqpeV*")) if path.is_dir() else [path]
        if len(files) != 1:
            raise ValueError("Specify exactly one GAP eqpeV file")
        eqp = Eqpev(files[0], casename=files[0].name.split(".")[0])
        ks, qp = eqp.get_KS_bandstructure(), eqp.get_QP_bandstructure()
        return ks, qp
    if code == "vasp":
        from mushroom.vasp import get_qp_energies_from_outcar as read
        filename = path / "OUTCAR" if path.is_dir() else path
        # Each call returns (BandStructure, kpts); it does not return both energies.
        return read(filename, qp_iteration=0, extract_KS=True)[0], read(filename)[0]
    raise NotImplementedError("QP pairs support aims, librpa, gap and vasp; got " + code)
