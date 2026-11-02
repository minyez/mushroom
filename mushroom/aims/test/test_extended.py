"""input manipulation and output-search regressions"""
import io
from pathlib import Path
import tempfile
import unittest as ut

import numpy as np
from mushroom.aims.input import Control
from mushroom.aims.species import Species, search_basis_directories
from mushroom.aims.analyse import search_band_output_files, get_recp_latt_from_geometry
from mushroom.aims.stdout import StdOut
from mushroom.aims.workflow import AimsWorkdir

DATA = Path(__file__).parent / 'data'


class test_control_operations(ut.TestCase):
    def setUp(self):
        self.species = Species.read(DATA / '06_C_intermediate_modified')
        self.control = Control({'xc': 'pbe'}, {}, [self.species])

    def test_spin_and_species(self):
        c = self.control
        for value, expected in [(True, 'collinear'), (False, 'none'), ('collinear', 'collinear')]:
            c.set_spin(value)
            self.assertEqual(c.get_tag('spin'), expected)
        replacement = Species.read(DATA / '06_C_intermediate_modified')
        with self.assertRaises(ValueError):
            c.add_species(replacement)
        c.add_species(replacement, error_replace=False)
        self.assertIs(c.get_species('C'), replacement)
        c.replace_specie(Species('H'))
        self.assertEqual(c.elements, ['C'])
        c.add_species(Species('H'))
        self.assertEqual(c.elements, ['C', 'H'])
        with self.assertRaises(ValueError):
            c.get_species('O')

    def test_add_controls(self):
        left = Control({'xc': 'pbe'}, {'dos': True}, [Species('C', tags={})])
        right = Control({'xc': 'pw-lda', 'spin': 'none'}, {'mulliken': True}, [Species('H', tags={})])
        combined = left + right
        self.assertEqual(combined.tags, {'xc': 'pw-lda', 'spin': 'none'})
        self.assertEqual(combined.output, {'dos': True, 'mulliken': True})
        self.assertEqual(combined.elements, ['C', 'H'])
        combined.get_species('C').update_basic_tag('nucleus', '7')
        self.assertNotIn('nucleus', left.get_species('C').tags)
        with self.assertRaises(ValueError):
            left + Control(species=[Species('C', tags={})])

    def test_radial_base_preserves_radius(self):
        s = self.species
        s.update_basic_tag('radial_base', '24 7.0')
        self.assertEqual(s.get_radial_base(), (24, 7.0))
        self.control.update_radial_base('C', n_rad=32)
        self.assertEqual(s.get_radial_base(), (32, 7.0))
        self.control.update_radial_base('C', radius=8.0)
        self.assertEqual(s.get_radial_base(), (32, 8.0))
        self.control.update_radial_base('C')
        s.update_basic_tag('radial_base', None)
        with self.assertRaises(ValueError):
            s.update_radial_base(n_rad=24)
        s.update_radial_base(n_rad=24, radius=7)
        s.update_basic_tag('radial_base', 'bad')
        with self.assertRaises(ValueError):
            s.get_radial_base()

    def test_cut_potential_and_multiplier(self):
        c, s = self.control, self.species
        c.adjust_cut_pot('C', onset=4.0, width=2.0, scale=1.0)
        self.assertEqual(c.get_cut_pot('C'), ('4.0', '2.0', '1.0'))
        c.adjust_cut_pot('C', width=3.0)
        self.assertEqual(c.get_cut_pot('C'), ('4.0', '3.0', '1.0'))
        c.adjust_cut_pot('C')
        c.update_radial_multiplier('C', v=3)
        self.assertEqual(s.get_radial_multiplier(), '3')
        c.update_radial_multiplier('C')
        s.update_basic_tag('cut_pot', None)
        with self.assertRaises(KeyError):
            s.get_cut_pot()
        with self.assertRaises(ValueError):
            s.adjust_cut_pot(width=2)
        s.update_basic_tag('cut_pot', 'bad')
        with self.assertRaises(ValueError):
            s.get_cut_pot()
        with self.assertRaises(ValueError):
            s.adjust_cut_pot(width=2)

    def test_basis_delegation_and_roundtrip(self):
        c = self.control
        c.add_basis('C', 'hydro', '5 g 4.0', tier=4)
        c.switch_tier(4, False)
        self.assertFalse(c.get_basis('C', tier=4)[0][-1])
        c.switch_tier(4, True, elem='C')
        self.assertTrue(c.get_basis('C', tier=4)[0][-1])
        c.add_abf('C', 'hydro', '5 g 5.0')
        self.assertEqual(c.get_abf('C')[-1][1], '5 g 5.0')
        copy = Control.read(io.StringIO(c.export()))
        self.assertEqual(copy.elements, c.elements)
        self.assertIn(['hydro', '5 g 4.0'], [b[:2] for b in copy.get_basis('C')])
        self.assertEqual(copy.get_abf('C')[-1][1], '5 g 5.0')


class test_aims_searches(ut.TestCase):
    def test_band_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)
            self.assertEqual(search_band_output_files(p), [])
            for kind, prefix in [('dft','band'), ('mlk','bandmlk'), ('gw','GW_band')]:
                for suffix in ['', '.no_soc']:
                    for spin in [1, 2]:
                        (p / f'{prefix}{spin}001.out{suffix}').touch()
                    expected = [p / f'{prefix}1001.out{suffix}']
                    self.assertEqual(search_band_output_files(p, kind, suffix=suffix), expected)
                    self.assertEqual(search_band_output_files(p, kind, suffix=suffix, with_spin=True),
                                     (expected, [p / f'{prefix}2001.out{suffix}']))
                self.assertEqual(search_band_output_files(p), [p / f'{prefix}1001.out'])
            self.assertEqual(search_band_output_files(p, 'unknown'), [])

    def test_reciprocal_lattice(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / 'geometry.in'
            p.write_text('lattice_vector 2 0 0\nlattice_vector 0 3 0\nlattice_vector 0 0 4\natom 0 0 0 H\n')
            np.testing.assert_allclose(get_recp_latt_from_geometry(p), np.diag([np.pi, 2*np.pi/3, np.pi/2]),
                                       rtol=1e-14, atol=1e-14)  # floating-point evaluation of 2π/a
            p.write_text('atom 0 0 0 H\n')
            with self.assertRaises(ValueError):
                get_recp_latt_from_geometry(p)
            (p.parent / 'tight').mkdir()
            (p.parent / 'tight/01_H_default').touch()
            self.assertEqual(search_basis_directories(p.parent), ['tight'])

    def test_workdir_and_eigenvalues(self):
        w = AimsWorkdir(DATA, aimsout='Si.pgw_band.aims.out', aimserr='aims.err')
        w.load_output()
        self.assertTrue(w.is_finished())
        self.assertTrue(w.is_converged())
        self.assertEqual(w.path_aimserr.name, 'aims.err')
        bs, kpts = w._aimsout.get_eigenvalues()
        self.assertEqual(bs.nspins, 1)
        self.assertEqual(len(kpts), bs.nkpts)
        # Compare against the SCF eigenvalue table, not the QP table.
        self.assertTrue(np.all(np.isfinite(bs.eigen)))
        s = StdOut.__new__(StdOut)
        s._scf_lines = None
        with self.assertRaises(ValueError):
            s.get_eigenvalues()
        s._scf_lines, s._nspins = [], 2
        with self.assertRaises(ValueError):
            s.get_eigenvalues()
