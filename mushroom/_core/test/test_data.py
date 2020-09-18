#!/usr/bin/env python
# -*- coding: utf-8 -*-
# pylint: disable=missing-function-docstring
"""test data manipulation facilities"""
import unittest as ut
import numpy as np

from mushroom._core.data import (conv_estimate_number,
                                 Data)

class test_number_conversion(ut.TestCase):
    """test number conversion"""

    def test_conv_estimate(self):
        self.assertEqual(conv_estimate_number("5.43(2)"), 5.432)
        self.assertEqual(conv_estimate_number("5.43(2)", reserved=False), 5.43)

class test_Data(ut.TestCase):
    """Test Data object"""
    def test_get(self):
        """test data extraction"""
        x = np.array((1.0, 2.0, 3.0))
        y = np.array((3.0, 4.0, 5.0))
        data = Data(x, y)
        self.assertListEqual([x, y], data.get(True))
        self.assertTrue(np.all(np.transpose([x, y]) == np.array(data.get())))

    def test_export(self):
        """test data export"""
        x = (1.0, 2.0, 3.0)
        y = (3.0, 4.0, 5.0)
        data = Data(x, y)
        s_normal = ["1.0 3.0",
                    "2.0 4.0",
                    "3.0 5.0"]
        s_transp = ["1.0 2.0 3.0",
                    "3.0 4.0 5.0"]
        s_normal_51f = ["  1.0   3.0",
                        "  2.0   4.0",
                        "  3.0   5.0"]
        s_transp_51f = ["  1.0   2.0   3.0",
                        "  3.0   4.0   5.0"]
        s_normal_51f_42f = ["  1.0 3.00",
                            "  2.0 4.00",
                            "  3.0 5.00"]
        s_transp_51f_42f = ["  1.0   2.0   3.0",
                            "3.00 4.00 5.00"]
        self.assertListEqual(s_normal, data.export(form="{:3.1f}"))
        self.assertListEqual(s_transp, data.export(form="{:3.1f}", transpose=True))
        self.assertListEqual(s_normal_51f, data.export(form="{:5.1f}"))
        self.assertListEqual(s_transp_51f, data.export(form="{:5.1f}", transpose=True))
        self.assertListEqual(s_normal_51f_42f, data.export(form=["{:5.1f}", "{:4.2f}"]))
        self.assertListEqual(s_transp_51f_42f, data.export(form=["{:5.1f}", "{:4.2f}"], transpose=True))
        


if __name__ == "__main__":
    ut.main()

