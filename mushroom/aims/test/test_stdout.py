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

            s.get_control()
            s.get_n_spin_kpt_band_basis()

            # key-method pair to check equality
            assert_equal = [
                ("nnodes", s.get_nnodes()),
                ("ntasks", s.get_ntasks()),
                ("nthreads", s.get_omp_threads()),
                ("nspins", s._nspins),
                ("nkpts", s._nkpts),
                ("nbands", s._nbands),
                ("nbasis", s._nbasis),
                ("nbasbas", s._nbasbas),
                ("is_finished", s.is_finished()),
            ]
            for k, v in assert_equal:
                if k in verify:
                    print("Testing key", k)
                    self.assertEqual(verify[k], v)

            if fn in fns_qp:
                qpbs, _ = s.get_QP_bandstructure()
                if "gwfundgap" in verify:
                    self.assertAlmostEqual(qpbs.fund_gap(), verify["gwfundgap"], places=4)

            if s.is_finished():
                s.get_cpu_time()
                s.get_wall_time()
                s.get_wall_time_total()


if __name__ == "__main__":
    ut.main()
