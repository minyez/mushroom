"""unittest of band plot helper functions"""
import unittest as ut

import numpy as np

from mushroom.visual.bandplot import bandplot
from mushroom.core.bs import random_band_structure
from mushroom.core.kpoints import KPathLinearizer

class test_bandplot(ut.TestCase):

    def test_random_bs(self):
        bs = random_band_structure(nkpts=6)
        kpts = np.array([
            [0., 0., 0.],
            [0.1, 0., 0.],
            [0.2, 0., 0.],
            [0.3, 0., 0.],
            [0.4, 0., 0.],
            [0.5, 0., 0.],
        ])
        kp = KPathLinearizer(kpts)
        bandplot(bs, kp)

if __name__ == "__main__":
    ut.main()
