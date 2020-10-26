#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
import pathlib
import unittest as ut

from mushroom import w2k

class test_struct(ut.TestCase):
    """test struct file processing"""
    def test_read(self):
        """read from test struct files"""
        p = pathlib.Path(__file__).parent
        with open(p / "data" / "struct.json", 'r') as fp:
            verifies = json.load(fp)
        dir_struct = p / "data"
        for f, verify in verifies.items():
            print("Testing {}".format(f))
            w2k.Struct.read(dir_struct / f)
            #for k, v in verify.items():
            #    self.assertEqual(dos.__getattribute__(k), v)

if __name__ == "__main__":
    ut.main()
