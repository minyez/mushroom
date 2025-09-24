#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import unittest as ut
import pathlib
import json

from mushroom.aims.band import decode_band_output_line, read_band_output, read_band_mulliken_output


class test_decode_band_output_line(ut.TestCase):
    # pylint: disable=C0301
    def test_general_line(self):
        lines = ("   1        0.2500000      0.5000000      0.7500000     2.00000       -6.35321     2.00000       -5.21600     2.00000       -4.64646     0.00000        8.25785",
                 "   2        0.2777778      0.5000000      0.7222222     2.00000       -6.45133     2.00000       -5.20909     2.00000       -4.54280     0.00000        8.30246"
                 )
        results = (
            ([0.25, 0.50, 0.75], [2.0, 2.0, 2.0, 0.0], [-6.35321, -5.21600, -4.64646, 8.25785]),
            ([0.2777778, 0.50, 0.7222222], [2.0, 2.0, 2.0, 0.0], [-6.45133, -5.20909, -4.54280, 8.30246]))

        for l, (kpt, occ, ene) in zip(lines, results):
            kpt_d, occ_d, ene_d = decode_band_output_line(l)
            self.assertListEqual(kpt, kpt_d)
            self.assertListEqual(occ, occ_d)
            self.assertListEqual(ene, ene_d)


class test_read_band_output(ut.TestCase):

    def test_read_testcases(self):
        datadir = pathlib.Path(__file__).parent / "data"
        testcases_json = datadir / "testcases_band.json"
        with testcases_json.open('r') as h:
            verifies = json.load(h)
        for case, verify in verifies.items():
            bandfiles = [datadir / x for x in verify.pop("files")]
            bs, kpts = read_band_output(*bandfiles)
            for k, v in verify.items():
                self.assertEqual(bs.__getattribute__(k), v)


class test_read_band_mulliken_output(ut.TestCase):

    def test_read_testcases(self):
        datadir = pathlib.Path(__file__).parent / "data"
        testcases_json = datadir / "testcases_bandmlk.json"
        with testcases_json.open('r') as h:
            verifies = json.load(h)
        for case, verify in verifies.items():
            print(f"Testing {case}")
            bandfiles = [datadir / x for x in verify.pop("files")]
            bandfiles_spin = None
            if "files_spin" in verify:
                bandfiles_spin = [datadir / x for x in verify.pop("files_spin")]
            print(f"- band files: {bandfiles} (spin down: {bandfiles_spin})")
            bs, kpts = read_band_mulliken_output(*bandfiles, bfiles_spin=bandfiles_spin)
            print("- band files parsed successfully")
            for k, v in verify.items():
                self.assertEqual(bs.__getattribute__(k), v)
                print(f"- verified {k}")


if __name__ == "__main__":
    ut.main()
