"""exercise public commands with isolated scientific input and scheduler stubs"""
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import unittest as ut
from unittest.mock import patch

import numpy as np
from click.testing import CliRunner
from mushroom.cli import main
from mushroom.cli.aims import _handle_tag_pair, _handle_elem_tag_pair
from mushroom.aims.input import Control
from mushroom.core.cell import Cell
from mushroom import hpc

AIMS = Path(__file__).resolve().parents[1] / 'aims/test/data'


class test_aims_commands_extended(ut.TestCase):
    def setUp(self):
        self.runner = CliRunner()
        self.isolation = self.runner.isolated_filesystem()
        self.isolation.__enter__()
        self.addCleanup(self.isolation.__exit__, None, None, None)

    def invoke(self, *args):
        result = self.runner.invoke(main, ['aims', *args])
        self.assertEqual(result.exit_code, 0, str(result.exception) + '\n' + result.output)
        return result.output

    def test_tag_decoding(self):
        for token in ['t', '.t.', 'true', '.true.']:
            self.assertEqual(_handle_tag_pair('key:'+token), ('key', True))
        for token in ['f', '.f.', 'false', '.false.']:
            self.assertEqual(_handle_elem_tag_pair('C:key:'+token), ('C', 'key', False))
        self.assertEqual(_handle_tag_pair('key'), ('key', None))
        self.assertEqual(_handle_tag_pair('xc:pbe'), ('xc', 'pbe'))
        with self.assertRaises(ValueError):
            _handle_elem_tag_pair('invalid')

    def test_control_editing(self):
        source = str(AIMS / 'BP.pgw_band.control.in')
        self.invoke('control', '-i', source, '-O', 'control.in', '-t', 'xc:pw-lda', 'spin:none',
                    '--ot', 'mulliken:t', '--st', 'B:radial_multiplier:3')
        c = Control.read('control.in')
        self.assertEqual(c.tags['xc'], 'pw-lda')
        self.assertEqual(c.get_species('B').get_radial_multiplier(), '3')
        self.assertEqual(c.output['mulliken'], True)
        self.invoke('control', '-i', source, '-O', 'empty.in', '--reload-species', '')
        self.assertEqual(Control.read('empty.in').elements, [])
        self.invoke('control', '-i', source, '-O', 'reload.in', '--reload-species',
                    str(AIMS / '06_C_intermediate_modified'))
        self.assertEqual(Control.read('reload.in').elements, ['C'])
        text = self.invoke('control', '-i', source, '--handle-basis', 'a:B:hydro:5 g 4.0')
        self.assertIn('5 g 4.0', text)
        result = self.runner.invoke(main, ['aims', 'control', '-i', source, '--handle-basis', 'x:B'])
        self.assertIsInstance(result.exception, ValueError)
        result = self.runner.invoke(main, ['aims', 'control'])
        self.assertIsInstance(result.exception, NotImplementedError)

    def test_prepare_control(self):
        text = self.invoke('prepare-control', '--xc', 'pbe', '--spin', '-k', '2', '3', '4')
        c = Control.read(io.StringIO(text))
        self.assertEqual(c.tags['spin'], 'collinear')
        self.assertEqual(c.tags['k_grid'], '2 3 4')
        self.assertEqual(c.tags['xc'], 'pbe')
        text = self.invoke('prepare-control', '--template', str(AIMS / 'BP.pgw_band.control.in'))
        self.assertIn('xc', text)
        Cell(np.eye(3)*5, ['C'], [[0,0,0]]).write('aims', 'geometry.in')
        defaults = Path('defaults/defaults_2020/intermediate')
        defaults.mkdir(parents=True)
        (defaults / '01_H_default').write_text('species H\n')
        shutil.copy(AIMS / '06_C_intermediate_modified', defaults / '06_C_default')
        with patch.dict(os.environ, AIMS_SPECIES_DEFAULTS=str(Path('defaults').resolve())):
            text = self.invoke('prepare-control', '-g', 'geometry.in')
        self.assertEqual(Control.read(io.StringIO(text)).elements, ['C'])

    def test_finish_and_dimensions(self):
        self.assertEqual(self.runner.invoke(main, ['aims', 'check-finish']).exit_code, 1)
        shutil.copy(AIMS / 'Si.pgw_band.aims.out', 'aims.out')
        self.assertIn('aims.out', self.invoke('check-finish'))
        self.assertIn('28', self.invoke('dim', 'aims.out'))

    def test_qp_corrections(self):
        source = str(AIMS / 'Si.pgw_kgrid_collinear.aims.out')
        for kind, name in [('x','sigx'), ('c','sigc'), ('xc','sigxc'), ('qp','qpcorr')]:
            with self.subTest(kind=kind):
                self.invoke('qp-corr', source, '--kind', kind, '--ref', 'vbm')
                text = Path(f'plot_{name}.agr').read_text()
                self.assertIn('@target G0.S0', text)
                self.assertIn('@type xy', text)
        self.invoke('qp-corr', source, '--ref', 'fermi', '-o', 'fermi.agr')
        self.assertTrue(Path('fermi.agr').is_file())

    def test_qp_dos_and_gap(self):
        source = str(AIMS / 'Si.pgw_kgrid_collinear.aims.out')
        self.invoke('qp-dos', source, '-o', 'qp.dat', '--filter-above-ef', '3')
        self.invoke('qp-dos', source, '-o', 'ks.dat', '--ks')
        for name in ['qp', 'ks']:
            data = np.loadtxt(name+'.dat')
            self.assertEqual(data.shape[1], 3)
            self.assertTrue(np.all(np.diff(data[:,0])>0))
            self.assertTrue(np.all(data[:,1]>=0))
            self.assertIn('#'+name.upper()+'-DOS', Path(name+'.dat').read_text())
        source = str(AIMS / 'ZrO2_sc222.pgw_kgrid.aims.out')
        output = self.invoke('qp-gap', source, '--value', '--use-occ-only')
        # Reference comes from the real-output fixture manifest.
        reference = json.loads((AIMS / 'aimsout.json').read_text())['ZrO2_sc222.pgw_kgrid.aims.out']['gwfundgap']
        self.assertAlmostEqual(float(output.split()[0]), reference, places=4)
        self.assertIn('gap', self.invoke('qp-gap', source, '--ks').lower())


class test_scheduler_commands(ut.TestCase):
    def test_sbatch_library(self):
        with patch.object(hpc.sp, 'run', return_value=subprocess.CompletedProcess([], 0, 'Submitted batch job 12\n', '')) as run:
            self.assertEqual(hpc.sbatch_submit('job.sh', extra_args=['--dependency=afterok:11'], cwd='calc'), (0,12))
            self.assertEqual(run.call_args.args[0], ['sbatch','--dependency=afterok:11','job.sh'])
            self.assertEqual(run.call_args.kwargs['cwd'], 'calc')
        with patch.object(hpc.sp, 'run', return_value=subprocess.CompletedProcess([], 1, 'failure', 'error')):
            self.assertEqual(hpc.sbatch_submit('job.sh'), (1,'failure'))
            self.assertFalse(hpc.is_slurm_enabled())
        with patch.object(hpc.sp, 'run', side_effect=FileNotFoundError):
            self.assertFalse(hpc.is_slurm_enabled())

    def test_submit_dependencies_and_stamps(self):
        runner = CliRunner()
        with runner.isolated_filesystem():
            cwd = Path.cwd()
            Path('job.sh').write_text('#!/bin/sh\ntrue\n')
            for name in ['a','b','c']:
                Path(name).mkdir()
            fake = Path('fake-sbatch').resolve()
            fake.write_text('#!'+sys.executable+'\nimport pathlib,sys\n'
                            'pathlib.Path("args").write_text("\\n".join(sys.argv[1:]))\n'
                            'print("Submitted batch job", {"a": 10, "b": 11, "c": 12}[pathlib.Path.cwd().name])\n')
            fake.chmod(0o755)
            with patch('mushroom.hpc.is_slurm_enabled', return_value=True):
                result = runner.invoke(main, ['job','submit','job.sh','--cmd',str(fake),'--only','a','b','c',
                                               '--dep','ok','--dep-jobid','9','--max','2'])
            self.assertEqual(result.exit_code, 0, str(result.exception))
            self.assertEqual(Path.cwd(), cwd)
            self.assertEqual(Path('a/args').read_text(), '--dependency=afterok:9\njob.sh')
            self.assertEqual(Path('b/args').read_text(), '--dependency=afterok:10\njob.sh')
            self.assertTrue(Path('a/.submitted').exists())
            self.assertTrue(Path('b/.submitted').exists())
            self.assertFalse(Path('c/.submitted').exists())
            with patch('mushroom.hpc.is_slurm_enabled', return_value=True):
                result = runner.invoke(main, ['job','submit','job.sh','--dry','--prefix','calc'])
            self.assertEqual(result.exit_code, 0, result.output)
            self.assertIn('already submitted', result.output)
            self.assertFalse(Path('c/.submitted').exists())
