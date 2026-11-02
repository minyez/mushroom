"""regressions for process execution, configuration and public I/O"""
import contextlib
import importlib
import io
import logging
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile
import unittest as ut
from unittest.mock import patch

import numpy as np
from click.testing import CliRunner

from mushroom import hpc, vasp, workflow
from mushroom.cli import main
from mushroom.core.cell import Cell
from mushroom.io import CellIO
from mushroom.visual import graceplot as gp


class test_public_regressions(ut.TestCase):
    def test_xml_unknown_key(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / 'vasprun.xml'
            p.write_text('<modeling></modeling>')
            with self.assertRaisesRegex(ValueError, 'unsupported|not supported'):
                vasp.read_xml('unknown', path=p)

    def test_xml_unfinished(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / 'vasprun.xml'
            p.write_text('<modeling><kpoints><varray name="kpointlist"><v>0 0 0</v><v>0.5 0 0</v></varray>')
            np.testing.assert_array_equal(vasp.read_xml('kpoints', path=p)['kpoints'], [[0, 0, 0], [0.5, 0, 0]])

    def test_merge_without_recoloring(self):
        _, g1 = gp.Plot.subplots()
        _, g2 = gp.Plot.subplots()
        g1.plot([0, 1], [1, 2], color='red')
        g2.plot([0, 1], [3, 4], color='blue')
        before = [ds.export() for ds in g1.datasets + g2.datasets]
        merged = gp.merge_graphs(g1, g2)
        self.assertEqual(len(merged.datasets), 2)
        self.assertEqual([ds.export()[1:] for ds in merged.datasets], [x[1:] for x in before])
        self.assertEqual(len(g1.datasets), 1)

    def test_grace_waits_and_checks(self):
        with patch.object(gp, 'HAS_GRACEBAT', '/bin/gracebat'), patch.object(gp.subprocess, 'run') as run:
            gp._run_gracebat('plot', 'fig.pdf', 'PDF', 100)
            self.assertEqual(run.call_args.kwargs, {'input': b'plot', 'check': True})
            run.side_effect = subprocess.CalledProcessError(1, 'gracebat')
            with self.assertRaises(subprocess.CalledProcessError):
                gp._run_gracebat('plot', 'fig.pdf', 'PDF', 100)

    def test_write_par_streams(self):
        p = gp.Plot()
        stream = io.StringIO()
        p.write_par(stream)
        expected = stream.getvalue()
        self.assertIn('page size', expected)
        with contextlib.redirect_stdout(io.StringIO()) as captured:
            p.write_par()
        self.assertEqual(captured.getvalue(), expected)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'plot.par'
            p.write_par(path)
            self.assertEqual(path.read_text(), expected)

    def test_invalid_logging_level(self):
        from mushroom.core.logger import get_logging_level
        with self.assertWarns(UserWarning):
            self.assertEqual(get_logging_level('foo'), logging.NOTSET)

    def test_import_environment(self):
        root = str(Path(__file__).resolve().parents[2])
        with tempfile.TemporaryDirectory() as tmp:
            env = dict(os.environ, PYTHONPATH=root, MUSHROOM_LOG='foo')
            env.pop('HOME', None)
            proc = subprocess.run([sys.executable, '-c', 'import mushroom.core.logger'], cwd=tmp,
                                  env=env, capture_output=True, text=True)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertFalse((Path(tmp) / 'mushroom.log').exists())

    def test_cellio_restore_on_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / 'POSCAR'
            Cell(np.eye(3), ['H'], [[0.1, 0.2, 0.3]]).write('vasp', filename=p)
            obj = CellIO(p)
            before = obj._cell.posi.copy()
            with patch.object(Cell, 'write', side_effect=OSError):
                with self.assertRaises(OSError):
                    obj.write(Path(tmp) / 'geometry.in', coord_system='C')
            self.assertEqual(obj._cell.coord_sys, 'D')
            np.testing.assert_array_equal(obj._cell.posi, before)

    def test_submit_does_not_change_cwd_on_failure(self):
        runner = CliRunner()
        with runner.isolated_filesystem():
            cwd = Path.cwd()
            Path('job.sh').write_text('#!/bin/sh\ntrue\n')
            Path('calc').mkdir()
            try:
                with patch('mushroom.hpc.is_slurm_enabled', return_value=True):
                    result = runner.invoke(main, ['job', 'submit', 'job.sh', '--cmd', '/missing/sbatch'])
                self.assertNotEqual(result.exit_code, 0)
                self.assertEqual(Path.cwd(), cwd)
                self.assertFalse(Path('calc/.submitted').exists())
            finally:
                os.chdir(cwd)

    def test_open_example_old_python(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / 'example.tar'
            with tarfile.open(p, 'w') as handle:
                info = tarfile.TarInfo('example/data')
                info.size = 2
                handle.addfile(info, io.BytesIO(b'ok'))
            extractall = tarfile.TarFile.extractall
            calls = []

            def legacy_extract(handle, path, **kwargs):
                calls.append(kwargs)
                self.assertNotIn('filter', kwargs)
                return extractall(handle, path, filter='fully_trusted')

            with patch.object(workflow, 'tarfile') as legacy:
                legacy.open = tarfile.open
                del legacy.data_filter
                with patch.object(tarfile.TarFile, 'extractall', legacy_extract):
                    with workflow.open_example(p) as example:
                        self.assertEqual((example / 'data').read_text(), 'ok')
            self.assertEqual(len(calls), 1)
