#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test gap related utitlies"""
import unittest as ut
import pathlib
import json
import numpy as np
from mushroom.gap import Eps

class test_eps(ut.TestCase):
    """.eps file"""
    def test_read_testdata(self):
        """read test eps files in data directory"""
        dir_eps = pathlib.Path(__file__).parent / "data"
        index_json = dir_eps / "gap_eps.json"
        with index_json.open('r') as fp:
            verifies = json.load(fp)
        for f, verify in verifies.items():
            print("Testing {}".format(f))
            fpath = dir_eps / f
            nomega = verify["nomega"]
            eps = Eps(str(fpath), is_q0=verify["is_q0"], kind=verify["kind"],
                      nbyte_recl=verify["nbyte_recl"])
            for k, v in verify.items():
                if isinstance(v, (int, str, bool)):
                    self.assertEqual(eps.__getattribute__(k), v)
            #self.assertEqual(eps.nomega, nomega)
            if eps.is_q0:
                emac_nlf_re = [eps.get_eps(i)[0, 0].real for i in range(nomega)]
                self.assertTrue(np.allclose(emac_nlf_re, verify["emac_nlf_re"]))

if __name__ == "__main__":
    ut.main()

