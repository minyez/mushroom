#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import unittest as ut
import pathlib
import json
import tempfile

from mushroom.aims.analyse import *


class test_analyse_stdout(ut.TestCase):

    def test_display_dimensions(self):
        datadir = pathlib.Path(__file__).parent / "data"
        index_json = datadir / "aimsout.json"
        with index_json.open('r') as h:
            fn_dict = json.load(h)

        # print only, not verify here
        for fn, _ in fn_dict.items():
            print(f"Testing {fn}")
            get_dimensions(datadir / fn)

    def test_is_finished_aimsdir(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = pathlib.Path(tmpdir)
            # empty directory, no output file
            self.assertIs(is_finished_aimsdir(path, use_regex=False), None)
            self.assertIs(is_finished_aimsdir(path, use_regex=True), None)
            # a fake stdout
            with open(path / "aims.out-1", 'w') as h:
                print("""
------------------------------------------------------------
          Invoking FHI-aims ...
  FHI-aims version      : 231130""", file=h)
            # unfinished aims.out
            self.assertIs(is_finished_aimsdir(path, "aims.out-*", use_regex=False), None)
            self.assertIs(is_finished_aimsdir(path, r"aims\.out-.*", use_regex=True), None)
            with open(path / "aims.out-2", 'w') as h:
                print("""
------------------------------------------------------------
          Invoking FHI-aims ...
  FHI-aims version      : 231130
          Have a nice day.
------------------------------------------------------------""", file=h)
            # finished aims.out
            self.assertEqual(
                os.path.basename(is_finished_aimsdir(path, "aims.out-*", use_regex=False)),
                "aims.out-2"
            )
            self.assertEqual(
                os.path.basename(is_finished_aimsdir(path, r"aims\.out-.*", use_regex=True)),
                "aims.out-2"
            )


if __name__ == "__main__":
    ut.main()
