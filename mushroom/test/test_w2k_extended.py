"""minimal WIEN2k projection records and structure conversion"""
import io
from pathlib import Path
import tempfile
import unittest as ut

import numpy as np
from mushroom import w2k
from mushroom.core.cell import Cell
from mushroom.io import CellIO


class test_w2k_extended(ut.TestCase):
    def test_qtl(self):
        text = ('title\nheader\nFERMI 0.5\nSPIN=1   NAT= 1\nATOM 1 MULT= 2 total,0,1\n'
                ' BAND 1\n1 1 0 0.1 0.2\n-1.0\n1 2 0 0.3 0.4\n-0.5\n'
                ' BAND 2\n1 1 0 0.5 0.6\n0.5\n1 2 0 0.7 0.8\n1.0\n')
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'test.qtl'
            path.write_text(text)
            bs = w2k.read_qtl(path)
            np.testing.assert_array_equal(bs.eigen, [[[-1,0.5],[-0.5,1]]])
            self.assertEqual(bs.unit, 'ry')
            weights, labels = w2k.read_qtl(path, data_only=True)
            np.testing.assert_allclose(weights, [[[[[0.2,0.4]], [[1.0,1.2]]], [[[0.6,0.8]], [[1.4,1.6]]]]],
                                       rtol=1e-15, atol=0)  # decimal-to-binary roundoff
            self.assertEqual(labels, ['s','p'])
            path.write_text(text.replace('SPIN=1', 'SPIN=2'))
            with self.assertRaises(NotImplementedError):
                w2k.read_qtl(path)
            path.write_text('title\nheader\nFERMI 0.5\ninvalid\n')
            with self.assertRaises(ValueError):
                w2k.read_qtl(path)

    def test_cellio_w2k_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            cell = Cell(np.eye(3)*3, ['Si'], [[0,0,0]])
            cell.write('vasp', tmp/'POSCAR')
            obj = CellIO(tmp/'POSCAR')
            obj.write(tmp/'test.struct', format='w2k')
            obj = CellIO(tmp/'test.struct')
            with self.assertRaises(NotImplementedError):
                obj.manipulate(primitize=True)
            obj.write(tmp/'copy.struct', format='w2k')
            obj.write(tmp/'roundtrip.vasp', coord_system='C')
            result = Cell.read_vasp(tmp/'roundtrip.vasp')
            np.testing.assert_allclose(result.latt, cell.latt, rtol=1e-6, atol=1e-6)  # struct lattice is six decimals
            self.assertEqual(result.atms, ['Si'])
            np.testing.assert_array_equal(result.posi, [[0,0,0]])

    def test_in1_add_and_export(self):
        paths = list((Path(__file__).parent/'data').glob('*.in1*'))
        self.assertTrue(paths)
        obj = w2k.In1.read(paths[0])
        obj.add_el(0, 4, e=0.4, einc=0.01, cont=False)
        self.assertTrue(obj.have_el(0,4))
        self.assertEqual(obj.lmax_at(0), 4)
        self.assertIn('STOP', obj.export())
        stream=io.StringIO()
        obj.write(stream)
        self.assertEqual(stream.getvalue().rstrip(), obj.export())
