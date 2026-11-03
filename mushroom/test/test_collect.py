"""Summary collection with real aims data and existing VASP excerpts."""
import ast
import csv
import json
import shutil
import tempfile
import unittest as ut
from pathlib import Path
from unittest.mock import patch
from click.testing import CliRunner
from mushroom.collect import collect, collect_dir, format_table, write_csv, plot_convergence
from mushroom.cli import main
from mushroom.aims.stdout import StdOut
from mushroom.visual.graceplot import Plot

ROOT = Path(__file__).resolve().parents[2]
AIMS = ROOT / 'mushroom/aims/test/data/Si.pgw_band.aims.out'


class test_collect(ut.TestCase):

    def test_aims_values(self):
        output = StdOut(AIMS)
        self.assertEqual(output.get_total_energy(), -15801.364247327)
        self.assertEqual(output.get_homo_lumo_gap(), .95778221)

    def test_directories(self):
        from mushroom.test.test_vasp import test_outcar
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name in ('k4', 'k6', 'k8', 'empty'):
                (root/name).mkdir()
            shutil.copy(AIMS, root/'k4/aims.out')
            # Preserve real output lines, dropping its unfinished tail only.
            (root/'k6/aims.out').write_text(''.join(AIMS.read_text().splitlines(keepends=True)[:2100]))
            (root/'k8/OUTCAR').write_text(test_outcar.text)
            shutil.copy(ROOT/'examples/vasp/EIGENVAL', root/'k8/EIGENVAL')
            rows = collect([root/'k4', root/'k6', root/'k8'], params={'k': r'k(\d+)$'})
            self.assertEqual([r['k'] for r in rows], [4, 6, 8])
            self.assertEqual([r['status'] for r in rows], ['finished', 'unfinished', 'finished'])
            self.assertEqual(rows[0]['energy'], -15801.364247327)
            self.assertEqual(rows[2]['energy'], -10.4)
            self.assertIsNone(rows[1]['wall_time'])
            self.assertIn('error', rows[1])
            self.assertEqual(collect_dir(root/'empty')['status'], 'missing')
            self.assertEqual(collect_dir(root/'absent')['status'], 'missing')
            for code in ('aims', 'vasp', 'w2k', 'librpa'):
                self.assertEqual(collect_dir(root/'empty', code)['status'], 'missing')
            self.assertEqual(collect_dir(root, 'qe')['status'], 'error')
            write_csv(rows, root/'summary.csv')
            with open(root/'summary.csv') as handle:
                reader = csv.DictReader(handle)
                self.assertEqual(len(list(reader)), 3)
                self.assertIn('k', reader.fieldnames)
            extra = collect([root/'empty'], params={'x': r'(empty)$', 'a': r'(9\.5)', 'b': r'(notfound)'})
            self.assertEqual(extra[0]['x'], 'empty')
            self.assertIsNone(extra[0]['a'])
            (root/'v1.5').mkdir()
            self.assertEqual(collect([root/'v1.5'], params={'v': r'v([\d.]+)$'})[0]['v'], 1.5)

    def test_table_errors(self):
        rows = [{'energy': -1.}, {'energy': -1.25}, {'energy': -1.5}]
        table = format_table(rows, fields=['energy'], delta='energy')
        self.assertEqual([line.split()[-1] for line in table[1:]], ['500', '250', '0'])
        self.assertEqual(rows[-1], {'energy': -1.5})
        self.assertIn('-', format_table([{}], delta='energy')[-1])
        self.assertEqual(len(format_table([])), 1)
        with self.assertRaises(ValueError):
            format_table(rows, delta='gap')
        with tempfile.TemporaryDirectory() as tmp:
            with patch('mushroom.collect.EXTRACTORS', {'test': lambda path: ('finished',
                        {'energy': lambda: 1/0, 'gap': lambda: 2})}):
                result = collect_dir(tmp, 'test')
            self.assertEqual(result['gap'], 2)
            self.assertIn('energy', result['error'])
        _, ax = Plot.subplots()
        plot_convergence([ax], [{'x': 2, 'y': 4}, {'x': 1, 'y': 2}, {'x': None}], [('x', 'y')])
        self.assertEqual(ax.ndata, 1)
        plot_convergence([ax], [{}], [('x', 'y')])

    def test_librpa_excerpt(self):
        tree = ast.parse((Path(__file__).parent/'test_librpa.py').read_text())
        excerpt = next(n.value for n in ast.walk(tree) if isinstance(n, ast.Constant)
                       and isinstance(n.value, str) and n.value.startswith('\nspin  1'))
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp)/'librpa.out').write_text(excerpt)
            row = collect_dir(tmp)
            self.assertEqual(row['status'], 'unfinished')
            self.assertAlmostEqual(row['gap'], 3.14558)
            self.assertIsNone(row['wall_time'])

    @ut.skip('Real WIEN2k case.scf and case.dayfile fixtures are required')
    def test_w2k_real_output(self):
        pass

    def test_cli(self):
        runner = CliRunner()
        with runner.isolated_filesystem():
            Path('k4').mkdir()
            Path('k6').mkdir()
            shutil.copy(AIMS, 'k4/aims.out')
            shutil.copy(AIMS, 'k6/aims.out')
            args = ['collect', '--pat', 'k*', '--param', r'k=k(\d+)', '--sort', 'k',
                    '--delta', 'energy', '--csv', 'rows.csv', '--json', 'rows.json',
                    '--plot', 'k:energy', 'k:gap', '--engine', 'grace', '-o', 'collect.agr']
            result = runner.invoke(main, args)
            self.assertEqual(result.exit_code, 0, str(result.exception))
            self.assertEqual(len(json.loads(Path('rows.json').read_text())), 2)
            self.assertTrue(Path('collect.agr').is_file())
            result = runner.invoke(main, ['collect', 'absent'])
            self.assertIn('Skipping', result.output)
            for extra in [['--param', 'bad'], ['--plot', 'bad']]:
                self.assertEqual(runner.invoke(main, ['collect'] + extra).exit_code, 2)
