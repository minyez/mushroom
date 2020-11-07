# -*- coding: utf-8 -*-
"""unittest of cube io"""
import unittest as ut
import tempfile

from mushroom.visual.cube import Cube

class test_cube(ut.TestCase):
    """test Cube object"""

    voxel_vecs = [[1.,0.,0.],[0.,2.,0.],[0.,0.,3.]]
    posi = [[0.,0.,0.],[1.,1.,1.]]
    atms = ["O", "O"]
    data = [
            [[0.,1.,2.],
             [3.,4.,5.],],
            [[10.,11.,12.],
             [13.,14.,15.],],
        ]

    def test_initialize(self):
        """initialization"""
        self.assertRaises(ValueError, Cube, self.data, self.voxel_vecs,
                          ["O",], self.posi)
        self.assertRaises(ValueError, Cube, self.data, self.voxel_vecs,
                          self.atms, self.posi, charges=[1.,])
        cube = Cube(self.data, self.voxel_vecs, self.atms, self.posi)

    def test_export(self):
        """export"""
        s = """{}
OUTER LOOP: X, MIDDLE LOOP: Y, INNER LOOP: Z
   3    0.000000    0.000000    0.000000
   2    1.000000    0.000000    0.000000
   2    0.000000    2.000000    0.000000
   3    0.000000    0.000000    3.000000
   8    0.000000    0.000000    0.000000    0.000000
   8    0.000000    1.000000    1.000000    1.000000
  0.00000E+00  0.10000E+01  0.20000E+01  0.30000E+01  0.40000E+01  0.50000E+01
  0.10000E+02  0.11000E+02  0.12000E+02  0.13000E+02  0.14000E+02  0.15000E+02"""\
        .format(Cube.default_comment)

    def test_read_after_write(self):
        """write"""
        tf = tempfile.NamedTemporaryFile(suffix=".cube")
        tf.close()

if __name__ == "__main__":
    ut.main()

