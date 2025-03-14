#!/usr/bin/env python
# -*- coding: utf-8 -*-
# pylint: disable=C0115,C0116
"""test cell functionality"""
import os
import pathlib
import tempfile
import json
import unittest as ut

import numpy as np
try:
    import spglib
except ImportError:
    spglib = None

from mushroom.core.cell import (Cell, CellError, latt_equal)
from mushroom.core.constants import ANG2AU, PI


class test_example_simple_cubic_lattice(ut.TestCase):
    """simple cubic"""

    a = 5.0
    latt = [[a, 0.0, 0.0],
            [0.0, a, 0.0],
            [0.0, 0.0, a]]
    atms = ["C"]
    frac = 0.5
    posi = [[frac, 0.0, 0.0]]

    cell = Cell(latt, atms, posi, unit="ang", coord_sys="D")

    def test_properties(self):
        """properties"""
        # unit
        self.assertEqual(self.cell.unit, "ang")
        # coordinate system
        self.assertEqual(self.cell.coord_sys, "D")
        # real space vectors
        self.assertTrue(np.array_equal(self.cell.a, self.latt))
        self.assertAlmostEqual(pow(self.a, 3), self.cell.vol)
        self.assertTrue(np.array_equal(self.cell.center, [0.5, 0.5, 0.5]))
        self.assertTupleEqual(self.cell.latt_consts,
                              (self.a, self.a, self.a, 90.0, 90.0, 90.0))
        # Reciprocal
        recp_2pi = np.array(self.latt, dtype=self.cell._dtype) / self.a**2
        self.assertTrue(np.allclose(self.cell.b_2pi, recp_2pi))
        self.assertTrue(np.allclose(self.cell.b, recp_2pi * 2.0 * PI))
        self.assertTrue(np.allclose(self.cell.blen, (2.0 * PI / self.a, ) * 3))
        # atom types
        self.assertEqual(1, self.cell.natm)
        self.assertListEqual(["C", ], self.cell.atom_types)
        self.assertDictEqual({0: "C"}, self.cell.type_mapping)
        self.assertListEqual([0, ], self.cell.type_index())

    def test_magic(self):
        self.assertEqual(1, len(self.cell))
        self.assertTupleEqual(tuple(self.posi[0]), tuple(self.cell[0]))

    def test_coord_conv(self):
        self.assertRaisesRegex(CellError,
                               "Only support \"D\" direct or fractional and \"C\" Cartisian.",
                               self.cell.__setattr__, "coord_sys", 'unknown')
        # direct2cart
        self.cell.coord_sys = 'C'
        self.assertTupleEqual(
            tuple(self.cell[0]), (self.frac * self.a, 0.0, 0.0))
        self.assertEqual("C", self.cell.coord_sys)
        # cart2direct
        self.cell.coord_sys = 'D'
        self.assertEqual(self.cell[0][0], self.frac)
        self.assertEqual("D", self.cell.coord_sys)

    def test_unit_conv(self):
        # ang2au
        self.cell.unit = 'au'
        latt = self.cell.get_cell()[0]
        if self.cell._dtype == 'float32':
            self.assertAlmostEqual(latt[0, 0], self.a * ANG2AU, places=5)
        else:
            self.assertAlmostEqual(latt[0, 0], self.a * ANG2AU)
        self.cell.coord_sys = 'C'
        # au2ang
        self.cell.unit = 'ang'
        self.assertAlmostEqual(self.a * self.frac, self.cell.posi[0, 0])
        self.cell.coord_sys = 'D'
        latt = self.cell.get_cell()[0]
        self.assertEqual(latt[0, 0], self.a)

    def test_scale(self):
        self.assertRaisesRegex(
            CellError, "scale must be positive real", self.cell.scale, '2')
        self.assertRaisesRegex(
            CellError, "scale must be positive real", self.cell.scale, -2.0)
        self.cell.scale(2)
        self.cell.scale(0.5)
        self.assertTrue(np.array_equal(self.cell.a, self.latt))

        c = self.cell.copy()
        c.coord_sys = "C"
        c.scale(0.5)
        self.assertTrue(np.array_equal(c.a, np.array(self.latt) * 0.5))

    def test_spglib_input(self):
        ip = self.cell.get_spglib_input()
        self.assertTupleEqual(
            (self.cell.latt, self.cell.posi, self.cell.type_index()), ip)


class cell_raise(ut.TestCase):

    def test_bad_cell(self):
        latt = [[5.0, 0.0, 0.0],
                [0.0, 0.0, 5.0]]
        atms = ["C"]
        posi = [[0.0, 0.0, 0.0]]
        self.assertRaises(CellError, Cell, latt, atms, posi)
        latt = [[5.0, 0.0],
                [0.0, 5.0, 0.0],
                [0.0, 0.0, 5.0]]
        self.assertRaises(CellError, Cell, latt, atms, posi)

    def test_bad_atoms_pos(self):
        """raise for bad atom positions"""
        latt = [[5.0, 0.0, 0.0],
                [0.0, 5.0, 0.0],
                [0.0, 0.0, 5.0]]

        atms = []
        posi = [[0.0, 0.0, 0.0]]
        self.assertRaises(CellError, Cell, latt, atms, posi)

        atms = ["C"]
        posi = [0.0, 0.0, 0.0]
        self.assertRaises(CellError, Cell, latt, atms, posi)

        atms = ["C"]
        posi = [[0.0, 0.0, 0.0], [0.1, 0.0, 0.0]]
        self.assertRaises(CellError, Cell, latt, atms, posi)

        atms = ["C", "C"]
        posi = [[0.0, 0.0, 0.0]]
        self.assertRaises(CellError, Cell, latt, atms, posi)


class cell_factory_method(ut.TestCase):
    """Test the class methods to generate commonly used lattice structure"""

    def test_bravais_cubic(self):
        pc = Cell.bravais_cP("C", a=5.0, coord_sys="D")
        self.assertEqual(1, len(pc))
        self.assertEqual("D", pc.coord_sys)
        bcc = Cell.bravais_cI("C", a=5.0, primitive=False, unit="au")
        self.assertEqual("au", bcc.unit)
        self.assertEqual(2, len(bcc))
        fcc = Cell.bravais_cF("C", a=5.0, primitive=False)
        self.assertEqual(4, len(fcc))
        # primitive cell
        pbcc = Cell.bravais_cI("C", a=5.0, primitive=True)
        self.assertEqual(1, len(pbcc))
        self.assertAlmostEqual(5.0 * np.sqrt(3.0) / 2.0, pbcc.alen[0])
        pfcc = Cell.bravais_cF("C", a=5.0, primitive=True)
        self.assertEqual(1, len(pfcc))
        self.assertAlmostEqual(5.0 * np.sqrt(0.5), pfcc.alen[0])

    def test_bravais_orth(self):
        oP = Cell.bravais_oP("C", a=1.0, b=2.0, c=3.0)
        self.assertEqual(len(oP), 1)
        self.assertEqual(oP.vol, 6.0)
        oI = Cell.bravais_oI("C")
        self.assertEqual(len(oI), 2)
        oF = Cell.bravais_oF("C")
        self.assertEqual(len(oF), 4)

    def test_typical_systems(self):
        # both conventional and primitive
        for p in [True, False]:
            c = Cell.diamond("C", primitive=p)
            self.assertEqual(8 - 6 * int(p), c.natm)
            Cell.anatase("Ti", "O", primitive=p)
            Cell.rutile("Ti", "O", primitive=p)
            c = Cell.zincblende("Zn", "O", primitive=p)
            self.assertEqual(8 - 6 * int(p), c.natm)
            c = Cell.rocksalt("Na", "Cl", primitive=p)
            self.assertEqual(8 - 6 * int(p), c.natm)
            c = Cell.delafossite(primitive=p)
            self.assertEqual(12 - 8 * int(p), c.natm)
        # primitive only
        Cell.perovskite("Ca", "Ti", "O")
        Cell.wurtzite("Zn", "O")
        Cell.pyrite()
        Cell.marcasite()
        Cell.MX2()


class cell_reader(ut.TestCase):
    """Test the reader classmethods"""

    def test_read_tempfile_json(self):
        self.assertRaisesRegex(CellError, "JSON file not found: None",
                               Cell.read_json, None)
        self.assertRaisesRegex(CellError, "JSON file not found: /abcdefg.json",
                               Cell.read_json, "/abcdefg.json")
        # raise for invalid json
        tf = tempfile.NamedTemporaryFile()
        with open(tf.name, 'w') as h:
            json.dump({}, h)
        self.assertRaisesRegex(CellError, "invalid JSON file for cell: {}".format(tf.name),
                               Cell.read_json, tf.name)

        jd = {"latt": [[5.0, 0.0, 0.0], [0.0, 5.0, 0.0], [0.0, 0.0, 5.0]]}
        with open(tf.name, 'w') as h:
            json.dump(jd, h)
        self.assertRaisesRegex(CellError,
                               "invalid JSON file for cell: {}. No {}".format(tf.name, "atms"),
                               Cell.read_json, tf.name)

        jd = {
            "latt": [[5.0, 0.0, 0.0], [0.0, 5.0, 0.0], [0.0, 0.0, 5.0]],
            "atms": ["C"],
        }
        with open(tf.name, 'w') as h:
            json.dump(jd, h)
        self.assertRaisesRegex(CellError,
                               "invalid JSON file for cell: {}. No {}".format(tf.name, "posi"),
                               Cell.read_json, tf.name)

        # JSON with factory key
        jd = {
            "factory": "zincblende",
            "atom1": "Zn",
            "a": 8.0, "unit": "au",
        }
        with open(tf.name, 'w') as h:
            json.dump(jd, h)
        self.assertRaisesRegex(CellError, "Required key not found in JSON: atom2",
                               Cell.read_json, tf.name)
        # add atom2 and dump again
        jd["atom2"] = "O"
        with open(tf.name, 'w') as h:
            json.dump(jd, h)
        c = Cell.read_json(tf.name)
        self.assertEqual(c.unit, 'au')
        self.assertEqual(c.comment, "Zincblende ZnO")
        self.assertAlmostEqual(512, c.vol)
        tf.close()

        # test one file in testdata, Cell_1.json is tested here
        _path = os.path.join(os.path.dirname(__file__),
                             'data', 'Cell_1.json')
        c = Cell.read_json(_path)
        self.assertEqual(c.unit, "ang")
        self.assertEqual(c.coord_sys, "D")
        self.assertEqual(c.natm, 2)
        self.assertListEqual(c.atms, ["C", "C"])

    def test_read_cif(self):
        dir_cif = pathlib.Path(__file__).parent / "data"
        index_json = dir_cif / "cif.json"
        with index_json.open('r') as fp:
            verifies = json.load(fp)
        for f, verify in verifies.items():
            print("Testing {}".format(f))
            fpath = dir_cif / f
            c = Cell.read(str(fpath), format="cif")
            for k, v in verify.items():
                cell_value = c.__getattribute__(k)
                msg = ">> error, different {}: {} != {}".format(k, v, cell_value)
                if isinstance(v, (int, float)):
                    self.assertEqual(cell_value, v, msg=msg)
                elif isinstance(v, list):
                    self.assertTrue(np.array_equal(cell_value, v), msg=msg)

    def test_read_wrapper_raise(self):
        self.assertRaisesRegex(ValueError, r"fail to get format",
                               Cell.read, "path-with-unknown-format")
        self.assertRaisesRegex(CellError, r"Unsupported reader",
                               Cell.read, "path.with-unknown-ext")

    def test_read_vasp(self):
        """read vasp POSCAR"""
        dir_poscar = pathlib.Path(__file__).parent / "data"
        index_json = dir_poscar / "poscar.json"
        with index_json.open('r') as fp:
            verifies = json.load(fp)
        for f, verify in verifies.items():
            print("Testing {}".format(f))
            fpath = dir_poscar / f
            c = Cell.read(str(fpath), format="vasp")
            for k, v in verify.items():
                cell_value = c.__getattribute__(k)
                msg = ">> error, different {}: {} != {}".format(k, v, cell_value)
                if isinstance(v, (int, float)):
                    self.assertEqual(cell_value, v, msg=msg)
                elif isinstance(v, list):
                    self.assertTrue(np.array_equal(cell_value, v), msg=msg)

    def test_read_tempfile_vasp(self):
        """test reading vasp POSCAR files created in temperary files"""

    def test_read_aims(self):
        """read aims geometry.in file"""
        dir_poscar = pathlib.Path(__file__).parent / "data"
        index_json = dir_poscar / "aimsgeometry.json"
        with index_json.open('r') as fp:
            verifies = json.load(fp)
        for f, verify in verifies.items():
            print("Testing {}".format(f))
            fpath = dir_poscar / f
            c = Cell.read(str(fpath), format="aims")
            for k, v in verify.items():
                cell_value = c.__getattribute__(k)
                msg = ">> error, different {}: {} != {}".format(k, v, cell_value)
                if isinstance(v, (int, float)):
                    self.assertEqual(cell_value, v, msg=msg)
                elif isinstance(v, list):
                    self.assertTrue(np.array_equal(cell_value, v), msg=msg)


class test_exporter(ut.TestCase):
    """test the exporter facilities"""
    latt = [[5.0, 0.0, 0.0], [0.0, 5.0, 0.0], [0.0, 0.0, 5.0]]
    atms = ["Cs", "Cl"]
    posi = [[0.0, 0.0, 0.0], [0.5, 0.5, 0.5]]
    c = Cell(latt, atms, posi)

    def test_export_abi(self):
        s = self.c.export_abi()
        c_copy = self.c.copy()
        c_copy.coord_sys = "C"
        s = c_copy.export_abi()

    def test_export_vasp(self):
        s = self.c.export_vasp()

    def test_export_json(self):
        s = self.c.export_json()

    def test_export_qe(self):
        s = self.c.export_qe()

    def test_export_qe_alat(self):
        s = self.c.export_qe_alat()

    def test_export_aims(self):
        s = self.c.export_aims()
        c_copy = self.c.copy()
        c_copy.coord_sys = "C"
        s = c_copy.export_aims()


class cell_select_dynamics(ut.TestCase):
    '''Test the functionality of selective dynamics
    '''

    def test_fix_all(self):
        c = Cell.bravais_cP("C")
        self.assertFalse(c.use_select_dyn)
        c = Cell.bravais_cP("C", all_relax=False)
        self.assertTrue(c.use_select_dyn)
        self.assertListEqual([False,] * 3, c.sd_flag(0))
        c = Cell.bravais_cI("C", all_relax=False, primitive=False)
        self.assertTrue(c.use_select_dyn)
        self.assertListEqual([[False,] * 3,] * 2, c.sd_flag())

    def test_relax_all(self):
        c = Cell.bravais_cI("C", all_relax=False, primitive=False,
                            select_dyn={1: [True, False, True]})
        c.relax_all()
        self.assertListEqual(c.sd_flag(1), [True, True, True])
        self.assertFalse(c.use_select_dyn)

    def test_fix_some(self):
        pc = Cell.bravais_cF("C", select_dyn={1: [False, True, True]})
        self.assertListEqual([True,] * 3, pc.sd_flag(0))
        self.assertListEqual([False, True, True, ], pc.sd_flag(1))

    def test_fix_by_set_method(self):
        pc = Cell.bravais_cF("C")
        pc.set_fix(0, 1)
        self.assertListEqual([False, False, False], pc.sd_flag(0))
        self.assertListEqual([False, False, False], pc.sd_flag(1))
        pc.set_fix(2, axis=1)
        self.assertListEqual([False, True, True], pc.sd_flag(2))
        pc.set_fix(3, axis=[2, 3])
        self.assertListEqual([True, False, False], pc.sd_flag(3))

    def test_relax_by_set_method(self):
        pc = Cell.bravais_cF("C", all_relax=False)
        pc.set_relax(0, 1)
        self.assertListEqual([True, True, True], pc.sd_flag(0))
        self.assertListEqual([True, True, True], pc.sd_flag(1))
        pc.set_relax(2, axis=1)
        self.assertListEqual([True, False, False], pc.sd_flag(2))
        pc.set_relax(3, axis=[2, 3])
        self.assertListEqual([False, True, True], pc.sd_flag(3))


class test_cut_calculation(ut.TestCase):

    def test_Rab_in_rcut(self):
        a = 5.0
        latt = [[a, 0.0, 0.0],
                [0.0, a, 0.0],
                [0.0, 0.0, a]]
        atms = ["H", "H"]
        posi = [[0., 0., 0.], [0.5, 0.5, 0.5]]
        c = Cell(latt, atms, posi)

        # for the same atom
        rabs = c.Rab_in_rcut(a - 0.01, 0, 0)
        self.assertEqual(len(rabs), 0)
        rabs = c.Rab_in_rcut(a + 0.01, 0, 0, axis=0)
        self.assertEqual(len(rabs), 2)
        rabs, _ = c.Rab_in_rcut(a + 0.01, 0, 0, return_iR=True)
        self.assertEqual(len(rabs), 6)
        rabs, _, _ = c.Rab_in_rcut(a * 1.43, 0, 0, return_iR=True, return_iR_Rablen=True)
        self.assertEqual(len(rabs), 6 + 12)
        rabs = c.Rab_in_rcut(a * 1.9, 0, 0)
        self.assertEqual(len(rabs), 6 + 12 + 8)

    def test_Gpq_in_gcut(self):
        a = 2.0 * PI
        latt = [[a, 0.0, 0.0],
                [0.0, a, 0.0],
                [0.0, 0.0, a]]
        atms = ["H",]
        posi = [[0., 0., 0.]]
        c = Cell(latt, atms, posi)
        g_pq = c.Gpq_in_gcut(0.95, 0.0)
        self.assertEqual(len(g_pq), 0)
        g_pq = c.Gpq_in_gcut(1.05, 0.0)
        self.assertEqual(len(g_pq), 6)
        g_pq, _ = c.Gpq_in_gcut(1.05, 0.0, axis=(0, 2), return_iG=True)
        self.assertEqual(len(g_pq), 4)


class cell_sort(ut.TestCase):
    """Test the sorting functionality of Cell
    """

    def test_direct_switch_cscl(self):
        _latt = [[1.0, 0.0, 0.0],
                 [0.0, 1.0, 0.0],
                 [0.0, 0.0, 1.0]]
        _atms = ["Cl", "Cs"]
        _posi = [[0.0, 0.0, 0.0], [0.5, 0.5, 0.5]]
        # Cs atom is fixed
        _fix = [False, False, False]

        _cell = Cell(_latt, _atms, _posi, select_dyn={1: _fix})
        self.assertListEqual([0], _cell.get_sym_index("Cl"))
        self.assertListEqual([0], _cell["Cl"])
        self.assertListEqual([1], _cell.get_sym_index("Cs"))
        self.assertListEqual([1], _cell["Cs"])
        _cell._switch_two_atom_index(0, 1)
        self.assertListEqual(_cell.atms, ["Cs", "Cl"])
        self.assertListEqual([0], _cell.get_sym_index("Cs"))
        self.assertListEqual([1], _cell.get_sym_index("Cl"))
        self.assertListEqual(_fix, _cell.sd_flag(0))

    # def test_sanitize_atoms_sic(self):
    #     _latt = [[1.0, 0.0, 0.0],
    #              [0.0, 1.0, 0.0],
    #              [0.0, 0.0, 1.0]]
    #     _atms = ["Si", "C", "Si", "Si", "C", "C", "Si", "C"]
    #     _posi = [[0.0, 0.0, 0.0],  # Si
    #             [0.25, 0.25, 0.25],  # C
    #             [0.0, 0.5, 0.5],  # Si
    #             [0.5, 0.0, 0.5],  # Si
    #             [0.25, 0.75, 0.75],  # C
    #             [0.75, 0.25, 0.75],  # C
    #             [0.5, 0.5, 0.0],  # Si
    #             [0.75, 0.75, 0.25]]  # C
    #     _posSanitied = [[0.0, 0.0, 0.0],  # Si
    #                     [0.0, 0.5, 0.5],  # Si
    #                     [0.5, 0.0, 0.5],  # Si
    #                     [0.5, 0.5, 0.0],  # Si
    #                     [0.25, 0.25, 0.25],  # C
    #                     [0.25, 0.75, 0.75],  # C
    #                     [0.75, 0.25, 0.75],  # C
    #                     [0.75, 0.75, 0.25]]  # C
    #     SiC = Cell(_latt, _atms, _posi,
    #                select_dyn={2: [False, False, False]})
    #     # _latt._sanitize_atoms()
    #     self.assertListEqual(list(sorted(_atms, reverse=True)),
    #                          SiC.atms)
    #     self.assertDictEqual({0: 'Si', 1: 'C'}, SiC.type_mapping)
    #     self.assertTrue(np.array_equal(SiC.pos,
    #                                    np.array(_posSanitied, dtype=SiC._dtype)))
    #     self.assertListEqual([False, False, False], SiC.sd_flag(1))

    def test_sort_posi_sic(self):
        """Test sorting atoms and their positions in SiC
        """
        latt = [[1.0, 0.0, 0.0],
                [0.0, 1.0, 0.0],
                [0.0, 0.0, 1.0]]
        atms = ["Si", "Si", "Si", "Si", "C", "C", "C", "C"]
        posi = [[0.0, 0.0, 0.0],  # Si
                [0.0, 0.5, 0.5],  # Si
                [0.5, 0.0, 0.5],  # Si
                [0.5, 0.5, 0.0],  # Si
                [0.25, 0.25, 0.25],  # C
                [0.25, 0.75, 0.75],  # C
                [0.75, 0.25, 0.75],  # C
                [0.75, 0.75, 0.25]]  # C
        posi_sorted = [0.5, 0.5, 0.0, 0.0, 0.75, 0.75, 0.25, 0.25]
        posi_sorted_rev = [0.0, 0.0, 0.5, 0.5, 0.25, 0.25, 0.75, 0.75]
        SiC = Cell(latt, atms, posi)
        # no need to sanitize atoms
        self.assertListEqual(atms, SiC.atms)
        self.assertDictEqual({0: 'Si', 1: 'C'}, SiC.type_mapping)
        for axis in range(3):
            SiC.sort_posi(axis=axis + 1)
            self.assertTrue(np.array_equal(np.array(posi_sorted, dtype=SiC._dtype),
                                           SiC.posi[:, axis]))
            SiC.sort_posi(axis=axis + 1, reverse=True)
            self.assertTrue(np.array_equal(np.array(posi_sorted_rev, dtype=SiC._dtype),
                                           SiC.posi[:, axis]))


class test_cell_manipulation(ut.TestCase):
    """Test manipulation methods for lattice and atoms
    """

    def test_add_atom_on_graphene(self):
        '''Test adding atoms in a graphene cell
        '''
        a = 5.2
        latt = [[a / 2, 0.0, 0.0],
                [-a / 2, a / 2 * np.sqrt(3.0), 0.0],
                [0.0, 0.0, 15.0]]
        atms = ["C", "C",]
        posi = [[0.0, 0.0, 0.5],
                [1.0 / 3, 2.0 / 3, 0.5],]
        gp = Cell(latt, atms, posi)
        self.assertRaisesRegex(CellError,
                               r"Invalid coordinate: *",
                               gp.add_atom, "H", [0.2, 0.3])
        self.assertRaisesRegex(CellError,
                               "atom should be string, received <class 'int'>",
                               gp.add_atom, 1, [0.2, 0.3, 0.4])
        gp.fix_all()
        gp.add_atom("H", [0.0, 0.0, 0.6], select_dyn=[False, False, True])
        self.assertEqual(gp.natm, 3)
        self.assertListEqual(gp.atms, ['C', 'C', 'H'])
        self.assertDictEqual(gp.type_mapping, {0: 'C', 1: 'H'})
        self.assertListEqual(gp.sd_flag(2), [False, False, True])

    def test_atom_arrange_after_add_atom(self):
        """Test if the atoms are correctly rearranged after adding new atom
        """
        a = 2.0
        latt = [[a, 0.0, 0.0],
                [0.0, a, 0.0],
                [0.0, 0.0, a]]
        atms = ["Na", "Cl", ]
        posi = [[0.0, 0.0, 0.0],
                [0.5, 0.5, 0.5], ]
        brokenNaCl = Cell(latt, atms, posi)
        brokenNaCl.add_atom('Na', [0.0, 0.5, 0.5])
        self.assertListEqual(brokenNaCl.atms, ['Na', 'Na', 'Cl'])
        brokenNaCl.add_atom('Na', [0.5, 0.0, 0.5])
        self.assertListEqual(brokenNaCl.atms, ['Na', 'Na', 'Na', 'Cl'])
        brokenNaCl.add_atom('Cl', [0.5, 0.0, 0.0])
        self.assertListEqual(brokenNaCl.atms, ['Na', 'Na', 'Na', 'Cl', 'Cl'])
        self.assertTrue(np.array_equal(brokenNaCl.posi,
                                       np.array([[0.0, 0.0, 0.0],
                                                 [0.0, 0.5, 0.5],
                                                 [0.5, 0.0, 0.5],
                                                 [0.5, 0.5, 0.5],
                                                 [0.5, 0.0, 0.0],], dtype=brokenNaCl._dtype)))


class test_diagonal_supercell(ut.TestCase):
    """test the supercell creation with diagonal transformation matrix"""
    latt = [[1.0, 0.0, 0.0],
            [0.0, 2.0, 0.0],
            [0.0, 0.0, 3.0]]
    atms = ["C", "Si"]
    posi = [[0.0, 0.0, 0.0],
            [0.5, 0.5, 0.5]]
    cell = Cell(latt, atms, posi, coord_sys="D")

    def test_mapping(self):
        atms = ["C", "Si", "C", "B"]
        posi = [[0.0, 0.0, 0.0],
                [0.0, 0.2, 0.0],
                [0.0, 0.3, 0.4],
                [0.5, 0.5, 0.5]]
        cell = Cell(self.latt, atms, posi, sort_atms=True)
        self.assertListEqual(cell.atms, ["C", "C", "Si", "B"])
        sc, mapping = cell.get_supercell(2, 1, 1, sort_atms=False, images_consec=False)
        self.assertListEqual(mapping, [0, 1, 2, 3, 0, 1, 2, 3])
        sc, mapping = cell.get_supercell(2, 1, 1, sort_atms=True, images_consec=False)
        self.assertListEqual(mapping, [0, 1, 0, 1, 2, 2, 3, 3])
        sc, mapping = cell.get_supercell(2, 1, 1, sort_atms=False, images_consec=True)
        self.assertListEqual(mapping, [0, 0, 1, 1, 2, 2, 3, 3])

    def test_211_sort(self):
        """test 2 1 1 supercell creation"""
        sclatt = [[2.0, 0.0, 0.0],
                  [0.0, 2.0, 0.0],
                  [0.0, 0.0, 3.0]]
        scatms = ["C", "C", "Si", "Si"]
        scposi = [[0.0, 0.0, 0.0],
                  [0.5, 0.0, 0.0],
                  [0.25, 0.5, 0.5],
                  [0.75, 0.5, 0.5]]
        sc, mapping = self.cell.get_supercell(2, 1, 1, sort_atms=True, images_consec=False)
        self.assertListEqual(scatms, sc.atms)
        self.assertListEqual(mapping, [0, 0, 1, 1])
        self.assertTrue(np.array_equal(sc.latt, np.array(sclatt, dtype=Cell._dtype)))
        self.assertTrue(np.array_equal(sc.posi, np.array(scposi, dtype=Cell._dtype)))

    def test_211_images_consec(self):
        """test 2 1 1 supercell creation"""
        sclatt = [[2.0, 0.0, 0.0],
                  [0.0, 2.0, 0.0],
                  [0.0, 0.0, 3.0]]
        scatms = ["C", "C", "Si", "Si"]
        scposi = [[0.0, 0.0, 0.0],
                  [0.5, 0.0, 0.0],
                  [0.25, 0.5, 0.5],
                  [0.75, 0.5, 0.5]]
        sc, mapping = self.cell.get_supercell(2, 1, 1, sort_atms=False, images_consec=True)
        self.assertListEqual(scatms, sc.atms)
        self.assertListEqual(mapping, [0, 0, 1, 1])
        self.assertTrue(np.array_equal(sc.latt, np.array(sclatt, dtype=Cell._dtype)))
        self.assertTrue(np.array_equal(sc.posi, np.array(scposi, dtype=Cell._dtype)))

    def test_121_sort(self):
        """test 1 2 1 supercell creation"""
        sclatt = [[1.0, 0.0, 0.0],
                  [0.0, 4.0, 0.0],
                  [0.0, 0.0, 3.0]]
        scatms = ["C", "C", "Si", "Si"]
        scposi = [[0.0, 0.0, 0.0],
                  [0.0, 0.5, 0.0],
                  [0.5, 0.25, 0.5],
                  [0.5, 0.75, 0.5]]
        sc, mapping = self.cell.get_supercell(1, 2, 1, sort_atms=True, images_consec=False)
        self.assertListEqual(scatms, sc.atms)
        self.assertTrue(np.array_equal(sc.latt, np.array(sclatt, dtype=Cell._dtype)))
        self.assertTrue(np.array_equal(sc.posi, np.array(scposi, dtype=Cell._dtype)))

    def test_112_sort(self):
        """test 1 1 2 supercell creation"""
        sclatt = [[1.0, 0.0, 0.0],
                  [0.0, 2.0, 0.0],
                  [0.0, 0.0, 6.0]]
        scatms = ["C", "C", "Si", "Si"]
        scposi = [[0.0, 0.0, 0.0],
                  [0.0, 0.0, 0.5],
                  [0.5, 0.5, 0.25],
                  [0.5, 0.5, 0.75]]
        sc, mapping = self.cell.get_supercell(1, 1, 2, sort_atms=True, images_consec=False)
        self.assertListEqual(scatms, sc.atms)
        self.assertTrue(np.array_equal(sc.latt, np.array(sclatt, dtype=Cell._dtype)))
        self.assertTrue(np.array_equal(sc.posi, np.array(scposi, dtype=Cell._dtype)))

    def test_122_sort(self):
        """test 1 2 2 supercell creation"""
        sclatt = [[1.0, 0.0, 0.0],
                  [0.0, 4.0, 0.0],
                  [0.0, 0.0, 6.0]]
        scatms = ["C", "C", "C", "C", "Si", "Si", "Si", "Si"]
        scposi = [[0.0, 0.0, 0.0],
                  [0.0, 0.5, 0.0],
                  [0.0, 0.0, 0.5],
                  [0.0, 0.5, 0.5],
                  [0.5, 0.25, 0.25],
                  [0.5, 0.75, 0.25],
                  [0.5, 0.25, 0.75],
                  [0.5, 0.75, 0.75]]
        sc, mapping = self.cell.get_supercell(1, 2, 2, sort_atms=True, images_consec=False)
        self.assertListEqual(scatms, sc.atms)
        self.assertListEqual(mapping, [0, 0, 0, 0, 1, 1, 1, 1])
        self.assertTrue(np.array_equal(sc.latt, np.array(sclatt, dtype=Cell._dtype)))
        # print(sc.posi, scposi)
        self.assertTrue(np.array_equal(sc.posi, np.array(scposi, dtype=Cell._dtype)))


class test_nondiagonal_supercell(ut.TestCase):

    def test_silicon_prim2conv(self):
        """test converting Si primitive cell to conventional cell"""
        latt = [[0.0, 2.7, 2.7],
                [2.7, 0.0, 0.7],
                [2.7, 2.7, 0.0]]
        atms = ["C", "Si"]
        posi = [[0.00, 0.00, 0.00],
                [0.25, 0.25, 0.25]]
        cell = Cell(latt, atms, posi, coord_sys="D")
        transmat = [-1, 1, 1,
                    1, -1, 1,
                    1, 1, -1]
        self.assertRaises(NotImplementedError, cell.get_supercell, *transmat)


class test_spglib_convert(ut.TestCase):

    def test_primitize(self):
        if spglib is None:
            return
        c = Cell.diamond("C")
        cprim = c.primitize()
        self.assertEqual(2, cprim.natm)


class test_cell_compare(ut.TestCase):
    def test_equal(self):
        c1 = Cell.diamond("Si", a=2.0)
        c2 = Cell.diamond("Si", a=2.0)
        self.assertTrue(c1 == c2)
        c3 = Cell.diamond("Si", a=2.0 * ANG2AU, unit="bohr")
        self.assertTrue(c1 == c3)
        c4 = Cell.diamond("C", a=2.0)
        self.assertFalse(c1 == c4)

    def test_same_latt(self):
        c1 = Cell.rocksalt("Na", "Cl", a=2.0)
        c2 = Cell.diamond("Si", a=2.0)
        self.assertTrue(latt_equal(c1, c2))


if __name__ == "__main__":
    ut.main()
