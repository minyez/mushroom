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
        dir_struct = pathlib.Path(__file__).parent / "data"
        index_json = dir_struct / "struct.json"
        with index_json.open('r') as fp:
            verifies = json.load(fp)
        for f, verify in verifies.items():
            print("Testing {}".format(f))
            fpath = dir_struct / f
            w2k.Struct.read(str(fpath))
            #for k, v in verify.items():
            #    self.assertEqual(dos.__getattribute__(k), v)

if __name__ == "__main__":
    ut.main()
