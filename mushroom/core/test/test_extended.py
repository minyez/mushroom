"""structure-format and occupation edge cases"""
import io
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest as ut

import numpy as np
from mushroom.core.cell import Cell
from mushroom.core.bs import BandStructure, BandStructureError


class test_cell_formats(ut.TestCase):
    def test_abacus_direct_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)/'STRU'
            c = Cell(np.eye(3)*4, ['Si'], [[0.25,0.25,0.25]], unit='bohr')
            text = c.export_abacus()
            self.assertIn('ATOMIC_SPECIES\nSi  28.085000  Si.upf', text)
            self.assertIn('LATTICE_CONSTANT\n1.000000000', text)
            self.assertIn('ATOMIC_POSITIONS\nDirect\nSi\n0.0\n1', text)
            p.write_text(text)
            result = Cell.read_abacus(p)
            np.testing.assert_array_equal(result.latt,c.latt)
            np.testing.assert_array_equal(result.posi,c.posi)
            self.assertEqual(result.atms,['Si'])
            c.unit='ang'
            p.write_text(c.export_abacus())
            result = Cell.read_abacus(p)
            result.unit='ang'
            np.testing.assert_allclose(result.latt,c.latt,rtol=1e-7,atol=1e-9)  # STRU's fixed conversion factor
            p.write_text('LATTICE_VECTORS\n1 0 0\n0 1 0\n0 0 1\n')
            with self.assertRaises(ValueError):
                Cell.read_abacus(p)
            p.write_text('ATOMIC_POSITIONS\nDirect\nSi\n0.0\n0\n')
            with self.assertRaises(ValueError):
                Cell.read_abacus(p)

    def test_abacus_cartesian(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'STRU'
            c=Cell(np.eye(3)*4,['H'],[[1,2,3]],unit='bohr',coord_sys='C')
            p.write_text(c.export_abacus())
            result=Cell.read_abacus(p)
            self.assertEqual(result.coord_sys,'C')
            np.testing.assert_array_equal(result.posi,[[1,2,3]])

    def test_centering(self):
        for coord_sys in ['D','C']:
            c=Cell(np.eye(3)*4,['H','H'],[[0.1,0.2,0.1],[0.3,0.4,0.3]])
            c.coord_sys=coord_sys
            c.centering(axis=3)
            self.assertEqual(c.coord_sys,coord_sys)
            c.coord_sys='D'
            np.testing.assert_allclose(c.posi,[[0.1,0.2,0.4],[0.3,0.4,0.6]],rtol=0,atol=1e-15)

    def test_export_restores_exact_values(self):
        c=Cell([[3,0.2,0],[0,4,0.1],[0,0,5]],['C'],[[0.3,0.4,0.5]],unit='bohr',coord_sys='C')
        latt,pos=c.latt.copy(),c.posi.copy()
        for format_ in ['qe','qe_alat','abi','vasp','aims']:
            with self.subTest(format=format_):
                c.export(format_)
                self.assertEqual((c.unit,c.coord_sys),('bohr','C'))
                np.testing.assert_array_equal(c.latt,latt)
                np.testing.assert_array_equal(c.posi,pos)

    def test_validation_survives_optimization(self):
        code='''
import numpy as np
from mushroom.core.ioutils import conv_string
from mushroom.core.cell import Cell
from mushroom.core.crystutils import periodic_duplicates_in_cell
checks = [lambda: conv_string('1', list),
          lambda: Cell(np.eye(3), ['H'], [[0,0,0]], coord_sys='bad'),
          lambda: periodic_duplicates_in_cell([1.1,0,0])]
for check in checks:
    try:
        check()
    except ValueError:
        pass
    else:
        raise RuntimeError('input validation was disabled')
'''
        root=Path(__file__).resolve().parents[3]
        with tempfile.TemporaryDirectory() as tmp:
            result=subprocess.run([sys.executable,'-O','-c',code],cwd=tmp,
                                  env=dict(os.environ,PYTHONPATH=str(root)),capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)


class test_occupations(ut.TestCase):
    def test_reset(self):
        bs=BandStructure([[[-2,1,3],[-1,2,4]]],unit='ev')
        bs.reset_occupations(efermi=0)
        np.testing.assert_array_equal(bs.occ,[[[1,0,0],[1,0,0]]])
        self.assertEqual(bs.fund_gap(),2)
        bs.reset_occupations(n_states=2)
        np.testing.assert_array_equal(bs.occ,[[[1,1,0],[1,1,0]]])
        self.assertEqual(bs.fund_gap(),1)
        bs.reset_occupations(occ=[[[1,0,0],[1,0,0]]])
        self.assertEqual(bs.fund_gap(),2)
        with self.assertRaises(ValueError):
            bs.reset_occupations()
        with self.assertRaises(BandStructureError):
            bs.reset_occupations(occ=[[1,0]])
