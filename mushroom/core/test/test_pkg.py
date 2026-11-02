#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test package facilities"""
import tempfile
import unittest as ut
from pathlib import Path

from mushroom.core.pkg import detect, detect_matchfn, detect_matchhead, detect_matchtail

class test_detect(ut.TestCase):
    """detect pacakges"""
    def test_detect_matchfn(self):
        """detect package by filename"""
        fns = {
            "INCAR": "vasp",
            ".": None,
            "MoS2.gpw": "gpaw",
            "diamond.vasp": "vasp",
            "Si.POSCAR": "vasp",
            }
        for fn, pkg in fns.items():
            self.assertEqual(pkg, detect_matchfn(fn),
                             msg=fn)

    def test_detect_matchhead(self):
        """detect package by the markers near the top of a file"""
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "unknown"
            p.write_text("&control\n  calculation = 'scf'\n/\n")
            self.assertEqual("qe", detect_matchhead(p))
            p.write_text("\n          Invoking FHI-aims ...\n")
            self.assertEqual("aims", detect_matchhead(p))
            # the marker is below the search depth
            p.write_text("\n\n\n          Invoking FHI-aims ...\n")
            self.assertIsNone(detect_matchhead(p))
            self.assertIsNone(detect_matchhead(tmp))

    def test_detect_matchtail(self):
        """detect package by the marker on the last line of a file"""
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "unknown"
            p.write_text("Elapsed time\n   Voluntary context switches:   10\n")
            self.assertEqual("vasp", detect_matchtail(p))
            p.write_text("   Voluntary context switches:   10\nmore output\n")
            self.assertIsNone(detect_matchtail(p))
            self.assertIsNone(detect_matchtail(tmp))

    def test_detect(self):
        """filename takes precedence, then head and tail of the file"""
        with tempfile.TemporaryDirectory() as tmp:
            vasp = Path(tmp) / "INCAR"
            vasp.write_text("&control\n")
            self.assertEqual("vasp", detect(vasp))
            head = Path(tmp) / "out.unknown"
            head.write_text("&control\n")
            self.assertEqual("qe", detect(head))
            tail = Path(tmp) / "log.unknown"
            tail.write_text("x\nVoluntary context switches: 1\n")
            self.assertEqual("vasp", detect(tail))
            none = Path(tmp) / "plain.unknown"
            none.write_text("nothing\n")
            self.assertIsNone(detect(none))
            self.assertEqual("unknown", detect(none, fail_with_ext=True))


if __name__ == "__main__":
    ut.main()

