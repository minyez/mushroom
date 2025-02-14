#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import unittest as ut
import pathlib
import json


from mushroom.aims.input import *


class test_control(ut.TestCase):

    # pylint: disable=R0914,R1702
    def test_control_read(self):
        dir_control = pathlib.Path(__file__).parent / "data"
        index_json = dir_control / "aimscontrol.json"
        with index_json.open('r') as h:
            verifies = json.load(h)
        for f, verify in verifies.items():
            print(f"Testing {f}")
            fpath = dir_control / f

            c = Control.read(fpath)
            for k, v in verify.items():
                if k == "elements":
                    self.assertListEqual(v, c.elements)
                if k == "tags":
                    for kt, vt in v.items():
                        self.assertEqual(c.get_tag(kt), vt)
                if k == "output":
                    for ko, vo in v.items():
                        vo_read = c.get_output(ko)
                        if ko == "band":
                            self.assertListEqual(verify["bandpathksym"], get_path_ksymbols(c.get_output("band")))
                            for band_read, band_veri in zip(vo_read, vo):
                                self.assertListEqual(band_read[0], band_veri[0])
                                self.assertListEqual(band_read[1], band_veri[1])
                                for i in range(2, 5):
                                    self.assertEqual(band_read[i], band_veri[i])
            c.export()

    def test_update_tag(self):
        ctrl = Control({}, {}, [])
        ctrl.update_tags({"sometag": 1, "sometag2": None, "booltag": ".false."})
        self.assertEqual(ctrl["sometag"], 1)
        self.assertEqual(ctrl["booltag"], False)
        self.assertNotIn("sometag2", ctrl.tags)

    def test_set_xc(self):
        ctrl = Control({}, {}, [])
        ctrl.set_xc("pbe0")
        ctrl.set_xc("pbe0-50")
        ctrl.set_xc("pbe0-75")
        ctrl.set_xc("hse06")

    def test_update_output_tag(self):
        ctrl = Control({}, {}, [])
        ctrl.update_output_tags({"sometag": 1, "sometag2": None, "booltag": ".false."})
        # they are not in the tags, but in output tags
        self.assertNotIn("sometag", ctrl.tags)
        # check output tags
        self.assertIn("sometag", ctrl.output)
        self.assertNotIn("sometag2", ctrl.output)
        self.assertEqual(ctrl.get_output("booltag"), False)

    def test_species_handling(self):
        dir_control = pathlib.Path(__file__).parent / "data"
        index_json = dir_control / "aimscontrol.json"
        with index_json.open('r') as h:
            cfiles = list(json.load(h).keys())
        if not cfiles:
            return
        # use the first to test
        cfile = cfiles[0]
        c = read_control(dir_control / cfile)
        elements = c.elements
        c.add_basis(elements[0], "hydro", "3 d 5.0")
        self.assertEqual("3 d 5.0", c.get_basis(elements[0], "hydro")[-1][1])
        c.switch_tier(1, True)
        c.switch_tier(2, True, elements[0])
        c.purge_species()


if __name__ == "__main__":
    ut.main()
