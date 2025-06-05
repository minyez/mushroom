#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import unittest as ut

from mushroom.core.utils import get_current_timestamp, raise_no_module


class test_get_current_timestamp(ut.TestCase):

    def test_now(self):
        get_current_timestamp()
        get_current_timestamp(with_weekday=True)

    def test_datetime_str(self):
        s = get_current_timestamp(with_weekday=True, datetime_str="2025-06-04 10:00:00")
        self.assertEqual(s, "2025-06-04 Wed 10:00:00")
        s = get_current_timestamp(with_weekday=True, datetime_str="2025-06-04")
        self.assertEqual(s, "2025-06-04 Wed 00:00:00")
        # Wrong weekday, but will be fixed by the datetime module
        s = get_current_timestamp(with_weekday=True, datetime_str="2025-06-04 Thu")
        self.assertEqual(s, "2025-06-04 Wed 00:00:00")


class test_check(ut.TestCase):
    """test check facilitiers"""

    def test_raise_no_module(self):
        """"""
        self.assertRaises(ModuleNotFoundError, raise_no_module,
                          None, "fake-module-name")
        self.assertRaises(ModuleNotFoundError, raise_no_module,
                          None, "fake-module-name", "for test")


if __name__ == '__main__':
    ut.main()
