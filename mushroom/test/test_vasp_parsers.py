"""VASP output fragments with hand-specified energies"""
import io
from pathlib import Path
import tempfile
import unittest as ut

import numpy as np
from mushroom import vasp


class test_outcar_fragments(ut.TestCase):
    def test_qp_iterations(self):
        text=('   ISPIN  = 1\n   k-points           NKPTS = 1\n'
              ' QP shifts <psi_nk| G(iteration)W_0 |psi_nk>: iteration 1\n'
              ' k-point 1 : 0.0 0.0 0.0\nheader\nheader\n'
              '1 -2 -3 0 0 0 0 2\n2 1 2 0 0 0 0 0\n\n'
              ' QP shifts iteration 2\n k-point 1 : 0.0 0.0 0.0\nheader\nheader\n'
              '1 -2 -4 0 0 0 0 2\n2 1 3 0 0 0 0 0\n\n')
        for kwargs,energies in [({},[-4,3]),({'qp_iteration':0},[-3,2]),({'extract_KS':True},[-2,1])]:
            bs,kpts=vasp.get_qp_energies_from_outcar(io.StringIO(text),**kwargs)
            np.testing.assert_array_equal(bs.eigen,[[energies]])
            np.testing.assert_array_equal(kpts,[[0,0,0]])
        with self.assertRaises(NotImplementedError):
            vasp.get_qp_energies_from_outcar(io.StringIO(text.replace('ISPIN  = 1','ISPIN  = 2')))
        with self.assertRaises(ValueError):
            vasp.get_qp_energies_from_outcar(io.StringIO('   ISPIN  = 1\n'))

    def test_wannier_energies(self):
        text=('   ISPIN  = 1\n   k-points           NKPTS = 2\n E-fermi : 0.0\n'
              ' k-point 1 : 0.0 0.0 0.0\nheader\n1 -2 2\n2 1 0\n\n'
              ' k-point 2 : 0.5 0.0 0.0\nheader\n1 -1 2\n2 2 0\n\n')
        bs,kpts=vasp.get_bandstructure_outcar_wannier(io.StringIO(text))
        np.testing.assert_array_equal(bs.eigen,[[[-2,1],[-1,2]]])
        np.testing.assert_array_equal(kpts,[[0,0,0],[0.5,0,0]])
        self.assertEqual(bs.efermi,0)
        with self.assertRaises(ValueError):
            vasp.get_bandstructure_outcar_wannier(io.StringIO(''))

    def test_warn_changed(self):
        with tempfile.TemporaryDirectory() as tmp:
            a,b=Path(tmp)/'a',Path(tmp)/'b'
            a.write_text('a'); b.write_text('b')
            with self.assertWarns(UserWarning) as caught:
                vasp.warn_changed(a,b)
            self.assertEqual(caught.filename,__file__)
            b.write_text('a')
            vasp.warn_changed(a,b)
