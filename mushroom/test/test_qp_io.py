"""QP reader integration with existing printed output samples."""
import ast
import tempfile
import unittest as ut
from pathlib import Path
from unittest.mock import patch
from click.testing import CliRunner
from mushroom.io import read_qp_pair
from mushroom.core.bs import qp_correction
from mushroom.cli import main

ROOT = Path(__file__).resolve().parents[2]
DATA = Path(__file__).parent / 'data'


class test_qp_io(ut.TestCase):

    def test_real_outputs(self):
        ks, qp = read_qp_pair(DATA / 'diamond_1.eqpeV_GW')
        self.assertAlmostEqual(qp_correction(ks, qp)[1][0], -21.579 - (-21.476))
        ks, qp = read_qp_pair(ROOT / 'mushroom/aims/test/data/Si.pgw_kgrid_collinear.aims.out')
        self.assertEqual(ks.nspins, 2)
        # Si output first printed QP state is band 11, line 6227.
        self.assertAlmostEqual(qp_correction(ks, qp)[1][0], -18.6424 - (-17.9579))
        # Reuse the existing LibRPA output excerpt verbatim; do not fabricate output.
        tree = ast.parse((Path(__file__).parent / 'test_librpa.py').read_text())
        excerpt = next(n.value for n in ast.walk(tree) if isinstance(n, ast.Constant)
                       and isinstance(n.value, str) and n.value.startswith('\nspin  1'))
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'librpa.out'
            path.write_text(excerpt)
            ks, qp = read_qp_pair(path)
            self.assertAlmostEqual(qp_correction(ks, qp)[1][0], -1882.70242 - (-1790.77527))
        with patch('mushroom.vasp.get_qp_energies_from_outcar', side_effect=[(ks, None), (qp, None)]) as read:
            a, b = read_qp_pair('OUTCAR', code='vasp')
            self.assertIs(a, ks)
            self.assertIs(b, qp)
            self.assertTrue(read.call_args_list[0].kwargs['extract_KS'])
        with self.assertRaises(NotImplementedError):
            read_qp_pair('none', code='qe')

    def test_cli_grace(self):
        runner = CliRunner()
        path = DATA / 'diamond_1.eqpeV_GW'
        result = runner.invoke(main, ['qp-corr', str(path), '--fit', '--data', '--emin', '-10', '--emax', '10'])
        self.assertEqual(result.exit_code, 0, str(result.exception))
        self.assertIn('slope', result.output)
        with runner.isolated_filesystem():
            result = runner.invoke(main, ['qp-corr', str(path), '--fit', '--engine', 'grace', '-o', 'qp.agr'])
            self.assertEqual(result.exit_code, 0, str(result.exception))
            self.assertTrue(Path('qp.agr').is_file())
