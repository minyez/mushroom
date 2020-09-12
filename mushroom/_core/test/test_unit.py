#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import unittest as ut

from mushroom._core.constants import ANG2AU, EV2RY
from mushroom._core.unit import EnergyUnit, LengthUnit, UnitError


class test_energy_unit(ut.TestCase):

    def test_raise_error(self):
        """test if UnitError is correctly raised"""
        self.assertRaisesRegex(UnitError, \
            r"allowed energy unit *", \
            EnergyUnit, "unknown-energy-unit")

    def test_conversion(self):
        """check if energy conversion unit is correct"""
        eu = EnergyUnit("ev")
        self.assertEqual(EV2RY, eu._get_eunit_conversion("ry"))


class test_length_unit(ut.TestCase):

    def test_raise_error(self):
        """test if UnitError is correctly raised"""
        self.assertRaisesRegex(UnitError, \
            r"allowed length unit *", \
            LengthUnit, "unknown-length-unit")
    
    def test_conversion(self):
        """check if length conversion unit is correct"""
        lu = LengthUnit("ang")
        self.assertEqual(ANG2AU, lu._get_lunit_conversion("au"))


if __name__ == '__main__':
    ut.main()

