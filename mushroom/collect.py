"""Collect calculation summaries without requiring a CLI or plotting package."""
import csv
import re
import os
from pathlib import Path
from mushroom.core.logger import loggers

FIELDS = ('path', 'code', 'status', 'energy', 'gap', 'gap_direct', 'efermi', 'nkpts', 'wall_time')
_logger = loggers['io']


def _aims(path):
    """Prepare independent FHI-aims summary fields."""
    from mushroom.aims.stdout import StdOut, AimsNotFinishedError
    filename = path / 'aims.out'
    if not filename.is_file():
        return 'missing', {}
    try:
        output = StdOut(filename)
    except AimsNotFinishedError:
        output = StdOut(filename, lazy_load=True)
    return ('finished' if output.is_finished() else 'unfinished', {
        'energy': output.get_total_energy, 'gap': output.get_homo_lumo_gap,
        'nkpts': output.get_n_kpts, 'wall_time': output.get_wall_time_total,
        'efermi': output.get_chemical_potential})


def _vasp(path):
    """Prepare independent VASP summary fields."""
    from mushroom.vasp import Outcar, read_eigen
    filename = path / 'OUTCAR'
    if not filename.is_file():
        return 'missing', {}
    output = Outcar(filename)
    fields = {'energy': output.get_total_energy, 'wall_time': lambda: output.wall_time}
    if (path / 'EIGENVAL').is_file():
        # Each field remains independently recoverable if another fails.
        fields.update(gap=lambda: read_eigen(path / 'EIGENVAL')[0].fund_gap(),
                      gap_direct=lambda: read_eigen(path / 'EIGENVAL')[0].direct_gap(),
                      efermi=lambda: read_eigen(path / 'EIGENVAL')[0].efermi,
                      nkpts=lambda: read_eigen(path / 'EIGENVAL')[0].nkpts)
    return 'finished' if output.is_finished else 'unfinished', fields


def _w2k(path):
    """Locate a unique WIEN2k SCF case for summary parsing."""
    from mushroom.w2k import read_scf_summary
    files = sorted(path.glob('*.scf'))
    if not files:
        return 'missing', {}
    if len(files) != 1:
        raise ValueError('Multiple WIEN2k cases; use separate directories')
    data = read_scf_summary(files[0])
    status = data.pop('status')
    return status, {k: lambda value=v: value for k, v in data.items()}


def _librpa(path):
    """Prepare LibRPA completion, gap and wall-time fields."""
    from mushroom.librpa import (_check_librpa_finished, read_quasi_particle_energies_stdout,
                                read_librpa_timing)
    filename = path / 'librpa.out'
    if not filename.is_file():
        return 'missing', {}
    finished = _check_librpa_finished(filename.read_text().splitlines())

    def wall_time():
        """Return reported total elapsed time, or None when timing is absent."""
        timing = read_librpa_timing(filename)
        return timing['total'][-1] if timing and timing['total'][0] >= 0 else None

    return 'finished' if finished else 'unfinished', {
        'gap': lambda: read_quasi_particle_energies_stdout(filename, kind='qp')[0].fund_gap(),
        'wall_time': wall_time}


EXTRACTORS = {'aims': _aims, 'vasp': _vasp, 'w2k': _w2k, 'librpa': _librpa}


def collect_dir(dirpath, code=None) -> dict:
    """Collect one directory, isolating failures of individual fields."""
    from mushroom.io import _detect_band_code
    path = Path(dirpath)
    row = dict.fromkeys(FIELDS)
    row.update(path=str(path), code=code, status='missing')
    errors = []
    if not path.is_dir():
        return row
    try:
        if code is None and not any(path.iterdir()):
            return row
        if code is None:
            from mushroom.detect import detect_codes
            if not detect_codes(path):
                return row
        code = _detect_band_code(path, code)
        row['code'] = code
        if code not in EXTRACTORS:
            raise ValueError('No summary extractor for ' + code)
        row['status'], fields = EXTRACTORS[code](path)
        for key, read in fields.items():
            try:
                row[key] = read()
            except Exception as err:  # A damaged field must not hide the other results.
                errors.append('{}: {}'.format(key, err))
    except Exception as err:  # One directory must not interrupt a scan.
        row['status'] = 'error'
        errors.append(str(err))
    if errors:
        row['error'] = '; '.join(errors)
        _logger.warning('%s: %s', path, row['error'])
    return row


def collect(dirpaths, code=None, params=None) -> list[dict]:
    """Collect directories and extract numeric or string parameters by regex."""
    rows = []
    for path in dirpaths:
        row = collect_dir(path, code)
        for name, pattern in (params or {}).items():
            match = re.search(pattern, os.path.relpath(path))
            value = match.group(1) if match else None
            if value is not None:
                for convert in (int, float):
                    try:
                        value = convert(value)
                        break
                    except ValueError:
                        pass
            row[name] = value
        rows.append(row)
    return rows


def format_table(rows, fields=None, delta=None) -> list[str]:
    """Return aligned text, optionally energy differences to the last row in meV."""
    fields = list(fields or FIELDS)
    values = [dict(row) for row in rows]
    if delta is not None:
        if delta != 'energy':
            raise ValueError('Only delta=energy is supported (meV)')
        fields.append('d_energy')
        reference = rows[-1].get('energy') if rows else None
        for row in values:
            value = row.get('energy')
            row['d_energy'] = None if reference is None or value is None else (value - reference) * 1000
    table = [fields]
    for row in values:
        table.append(['-' if row.get(key) is None else
                      ('{:.8g}'.format(row[key]) if isinstance(row[key], float) else str(row[key]))
                      for key in fields])
    widths = [max(len(row[i]) for row in table) for i in range(len(fields))]
    return ['  '.join(value.ljust(width) for value, width in zip(row, widths)).rstrip() for row in table]


def write_csv(rows, path, fields=None):
    """Write rows with stable field order, preserving extra scanned parameters."""
    fields = list(fields or dict.fromkeys(list(FIELDS) + [key for row in rows for key in row]))
    with open(path, 'w', newline='', encoding='utf-8') as handle:
        writer = csv.DictWriter(handle, fields, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(rows)


def plot_convergence(axes, rows, pairs):
    """Plot numeric field pairs, sorting each curve by its horizontal variable."""
    from mushroom.visual.axes import wrap_axes
    for ax, (xfield, yfield) in zip(axes, pairs):
        points = sorted((row[xfield], row[yfield]) for row in rows
                        if isinstance(row.get(xfield), (float, int)) and isinstance(row.get(yfield), (float, int)))
        adapter = wrap_axes(ax)
        if points:
            x, y = zip(*points)
            adapter.line(x, y, color='blue', ls='solid', marker='o')
        adapter.set_xlabel(xfield)
        adapter.set_ylabel(yfield)
