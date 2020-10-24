#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""test io utitlies"""
import unittest as ut
from mushroom.core.ioutils import split_comma, decode_int_range

class test_string_decoding(ut.TestCase):
    """string decoding"""
    def test_decode_int_range(self):
        self.assertListEqual(decode_int_range("5~9"), [5, 6, 7, 8, 9])
        self.assertListEqual(decode_int_range("vbm+5~+6"),
                             ["vbm+5", "vbm+6"])
        self.assertListEqual(decode_int_range("cbm-1~+2"),
                             ["cbm-1", "cbm+0", "cbm+1", "cbm+2"])

    def test_split_comma(self):
        self.assertListEqual(split_comma("5,6,9"), ["5", "6", "9"])
        self.assertListEqual(split_comma("2,6,9", int), [2, 6, 9])
        self.assertListEqual(split_comma("2,abc,9", int), [2, "abc", 9])
        self.assertListEqual(split_comma("a-2~1,9", int),
                             ["a-2", "a-1", "a+0", "a+1", 9])

if __name__ == "__main__":
    ut.main()
