"""Analytic parabolic masses on physical, segmented paths."""
import unittest as ut
import numpy as np
from mushroom.core.bs import BandStructure, BandPathData, effective_mass
from mushroom.core.kpoints import KPathLinearizer
from mushroom.core.constants import HBAR2_OVER_2ME_EV_ANG2 as H2M


class test_effective_mass(ut.TestCase):

    def make_data(self, fraction):
        kpts = np.column_stack([fraction, np.zeros((len(fraction), 2))])
        k = fraction * 2 * np.pi / 4.
        energies = np.column_stack([H2M / -.3 * k**2, 2 + H2M / .5 * k**2])
        return BandPathData(BandStructure(energies[None], efermi=1.), kpts,
                            np.eye(3) * 2 * np.pi / 4., ['Gamma', 'X'])

    def test_parabolas(self):
        data = self.make_data(np.linspace(0, .5, 21))
        self.assertAlmostEqual(H2M, 3.809982, places=5)
        for unit in ('ev', 'ry', 'au'):
            data.bs.unit = unit
            for ib, mass in [('cbm', .5), ('vbm', -.3)]:
                result = effective_mass(data.bs, data.kpath(), ib, None, side='right')
                self.assertAlmostEqual(result['right'], mass, places=9)
                self.assertIsNone(result['left'])
                self.assertEqual(result['right_label'], 'Gamma→X')
        result = effective_mass(data.bs, data.kpath(True), 1, 0)
        self.assertAlmostEqual(result['right'], .5, places=9)
        with self.assertRaisesRegex(ValueError, 'reciprocal lattice'):
            effective_mass(data.bs, KPathLinearizer(data.kpts), 1, 0)
        for kwargs in [dict(side='bad'), dict(ispin=2), dict(npoints=0)]:
            with self.assertRaises(ValueError):
                effective_mass(data.bs, data.kpath(), 1, 0, **kwargs)
        self.assertIsNone(effective_mass(data.bs, data.kpath(), 1, 0, npoints=2)['right'])

    def test_segments(self):
        data = self.make_data(np.r_[np.linspace(.5, 0, 11), np.linspace(.05, .5, 10)])
        data.ksymbols = ['X', 'Gamma', 'X']
        for key in ('left', 'right'):
            self.assertAlmostEqual(effective_mass(data.bs, data.kpath(), 'cbm', 10, npoints=30)[key], .5)
        # A following segment has a different curvature. A fit at its own endpoint
        # must not draw points across the turning point at Gamma.
        data.bs._eigen[0, 11:, 1] = 2 + 2 * (data.bs.eigen[0, 11:, 1] - 2)
        result = effective_mass(data.bs, data.kpath(), 'cbm', 10, npoints=30)
        self.assertAlmostEqual(result['left'], .5)
        self.assertAlmostEqual(result['right'], .25)
        result = effective_mass(data.bs, data.kpath(), 'cbm', 20, npoints=30)
        self.assertAlmostEqual(result['left'], .25)
        self.assertIsNone(result['right'])

