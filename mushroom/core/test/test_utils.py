#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import unittest as ut

from mushroom.core.utils import get_current_timestamp


class test_get_current_timestamp(ut.TestCase):

    def test_now(self):
        s = get_current_timestamp()
        s = get_current_timestamp(with_weekday=True)

    def test_datetime_str(self):
        s = get_current_timestamp(with_weekday=True, datetime_str="2025-06-04 10:00:00")
        self.assertEqual(s, "2025-06-04 Wed 10:00:00")
        s = get_current_timestamp(with_weekday=True, datetime_str="2025-06-04")
        self.assertEqual(s, "2025-06-04 Wed 00:00:00")
        # Wrong weekday, but will be fixed by the datetime module
        s = get_current_timestamp(with_weekday=True, datetime_str="2025-06-04 Thu")
        self.assertEqual(s, "2025-06-04 Wed 00:00:00")


if __name__ == '__main__':
    ut.main()
