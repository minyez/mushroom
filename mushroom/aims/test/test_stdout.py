#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# pylint: disable=C0115,C0116
"""test for aims functionality"""
import unittest as ut
import pathlib
import json

from mushroom.aims.stdout import StdOut


class test_stdout(ut.TestCase):
    """testing reading the standard output"""

    # pylint: disable=R0201
    def test_aimsout_reading(self):
        fns_qp = ["mole_ZnO.gw.aims.out", "ZrO2_sc222.pgw_kgrid.aims.out"]
        dir_control = pathlib.Path(__file__).parent / "data"
        index_json = dir_control / "aimsout.json"
        with index_json.open('r') as h:
            fn_dict = json.load(h)
        for fn, verify in fn_dict.items():
            print(f"Testing {fn}")
            s = StdOut(dir_control / fn)
            if fn in fns_qp:
                qpbs, _ = s.get_QP_bandstructure()
                if "gwfundgap" in verify:
                    self.assertAlmostEqual(qpbs.fund_gap(), verify["gwfundgap"], places=4)


if __name__ == "__main__":
    ut.main()
