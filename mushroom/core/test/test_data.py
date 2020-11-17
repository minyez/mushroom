#!/usr/bin/env python
# -*- coding: utf-8 -*-
# pylint: disable=missing-function-docstring
"""test data manipulation facilities"""
import unittest as ut
import numpy as np

from mushroom.core.data import (conv_estimate_number,
                                get_divisors, get_mutual_primes, closest_frac,
                                reshape_2n_float_n_cmplx,
                                Data)

class test_number_conversion(ut.TestCase):
    """test number conversion"""

    def test_conv_estimate(self):
        self.assertEqual(conv_estimate_number("5.43(2)", reserved=True), 5.432)
        self.assertEqual(conv_estimate_number("5.43(2)", reserved=False), 5.43)


class test_fraction(ut.TestCase):
    """test the functionality of finding minimal fractions"""
    def test_get_divisors(self):
        """divisors of integer"""
        self.assertListEqual([2, 4, 8], get_divisors(8))
        self.assertListEqual([2, 3, 4, 6, 9, 12, 18, 36], get_divisors(36))

    def test_get_mutual_primes(self):
        """mutual primes of integer"""
        self.assertListEqual([1, 3, 7, 9], get_mutual_primes(10))
        self.assertListEqual([1, 2, 4, 7, 8, 11, 13, 14], get_mutual_primes(15))

    def test_find_truefrac(self):
        """get the closest fraction number closest to a decimal"""
        self.assertEqual("1/3", closest_frac(0.3333, ret=0))
        self.assertEqual("1/3", closest_frac(0.333, ret=0))
        self.assertEqual("1/3", closest_frac(0.33330000, ret=0))
        self.assertEqual("2/3", closest_frac(0.667, ret=0))
        self.assertNotEqual("1/5", closest_frac(0.1, ret=0))
        self.assertEqual("2/3", closest_frac(0.6666, thres=0.0001, ret=0))

class test_Data(ut.TestCase):
    """Test Data object"""
    def test_raise(self):
        x = [1, 2]
        y = [3, 4]
        e = [0.1, 0.2, 0.3]
        self.assertRaises(ValueError, Data, x, y + [5,])
        self.assertRaises(ValueError, Data, x, y, dx=e)

    def test_get(self):
        """test data extraction"""
        x = np.array((1.0, 2.0, 3.0))
        y = np.array((3.0, 4.0, 5.0))
        xy = np.array([x, y])
        data = Data(x, y)
        self.assertTrue(np.all(xy == data.get()))
        self.assertTrue(np.all(np.transpose(xy) == np.array(data.get(True))))

    def test_export(self):
        """test data export"""
        x = (1.0, 2.0, 3.0)
        y = (3.0, 4.0, 5.0)
        data = Data(x, y)
        s_transp = ["1.0 3.0",
                    "2.0 4.0",
                    "3.0 5.0"]
        s_normal = ["1.0 2.0 3.0",
                    "3.0 4.0 5.0"]
        s_transp_51f = ["  1.0   3.0",
                        "  2.0   4.0",
                        "  3.0   5.0"]
        s_normal_51f = ["  1.0   2.0   3.0",
                        "  3.0   4.0   5.0"]
        s_transp_51f_42f = ["  1.0 3.00",
                            "  2.0 4.00",
                            "  3.0 5.00"]
        s_normal_51f_42f = ["  1.0   2.0   3.0",
                            "3.00 4.00 5.00"]
        self.assertListEqual(s_normal, data.export(form="{:3.1f}"))
        self.assertListEqual(s_transp, data.export(form="{:3.1f}", transpose=True))
        self.assertListEqual(s_normal_51f, data.export(form="{:5.1f}"))
        self.assertListEqual(s_transp_51f, data.export(form="{:5.1f}", transpose=True))
        self.assertListEqual(s_normal_51f_42f, data.export(form=["{:5.1f}", "{:4.2f}"]))
        self.assertListEqual(s_transp_51f_42f,
                             data.export(form=["{:5.1f}", "{:4.2f}"], transpose=True))


class test_reshape(ut.TestCase):
    """reshape facility"""
    def test_reshape_2n_floats(self):
        fdata = [1.0, 2.0, 3.0, 4.0]
        cdata = [1.0+2.0j, 3.0+4.0j]
        self.assertTrue(np.array_equal(reshape_2n_float_n_cmplx(fdata), cdata))

if __name__ == "__main__":
    ut.main()

