# -*- coding: utf-8 -*-
import unittest as ut
import os
import pathlib
import tempfile

from mushroom.io import CellIO


class test_CellIO(ut.TestCase):

    CELL_TEMPLATE = """FeS2
    1.000000
    5.418318     0.000000     0.000000
   -0.000000     5.418318     0.000000
   -0.000000    -0.000000     5.418318
     S     Fe
     8      4
direct
    0.115000     0.885000     0.385000 	 # S
    0.385000     0.115000     0.885000 	 # S
    0.885000     0.385000     0.115000 	 # S
    0.615000     0.615000     0.615000 	 # S
    0.885000     0.115000     0.615000 	 # S
    0.615000     0.885000     0.115000 	 # S
    0.115000     0.615000     0.885000 	 # S
    0.385000     0.385000     0.385000 	 # S
    0.500000     0.500000     0.000000 	 # Fe
    0.000000     0.500000     0.500000 	 # Fe
    0.500000     0.000000     0.500000 	 # Fe
    0.000000     0.000000     0.000000 	 # Fe
"""
    CELL_TEMPLATE_FORMAT = "vasp"

    def test_read(self):
        tf = tempfile.NamedTemporaryFile()

        with open(tf.name, 'w') as h:
            h.write(self.CELL_TEMPLATE)
        self.assertRaises(ValueError, CellIO, tf.name, format="non-existing-reader")

        tf.close()

    def test_manipulate(self):
        tf = tempfile.NamedTemporaryFile()

        with open(tf.name, 'w') as h:
            h.write(self.CELL_TEMPLATE)

        cellio = CellIO(tf.name, format=self.CELL_TEMPLATE_FORMAT)
        cellio.manipulate(standardize=True)
        cellio.manipulate(primitize=True)
        cellio.manipulate(supercell=[1, 1, 2])

        tf.close()

    def test_write(self):
        td = tempfile.TemporaryDirectory()
        tdpath = pathlib.Path(td.name)
        infile = tdpath / "POSCAR"
        with open(infile, 'w') as h:
            h.write(self.CELL_TEMPLATE)
        cellio = CellIO(infile)

        # print to stdout when output file is None
        cellio.write(None)

        # print to a file with detectable extension
        for ext in ["vasp", "struct"]:
            outfile = tdpath / ("test." + ext)
            cellio.write(outfile)

        # print to a file with unknown extension
        outfile = tdpath / "test.abcd"
        cellio.write(outfile)

        td.cleanup()


if __name__ == "__main__":
    ut.main()
