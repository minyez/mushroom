# -*- coding: utf-8 -*-
"""test detection of calculation code in a directory"""
import tempfile
import unittest as ut
from pathlib import Path

from mushroom.detect import detect_codes


def _touch(dirpath: Path, *names, content: str = ""):
    for name in names:
        p = dirpath / name
        if name.endswith("/"):
            p.mkdir(parents=True)
        else:
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content)


class test_detect_codes(ut.TestCase):

    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.tmpdir = Path(self._tmpdir.name)

    def tearDown(self):
        self._tmpdir.cleanup()

    def codes(self):
        return [r.code for r in detect_codes(self.tmpdir)]

    def test_empty(self):
        self.assertEqual(self.codes(), [])

    def test_not_a_directory(self):
        _touch(self.tmpdir, "INCAR")
        self.assertRaises(NotADirectoryError, detect_codes, self.tmpdir / "INCAR")

    def test_vasp(self):
        _touch(self.tmpdir, "INCAR", "POSCAR", "KPOINTS")
        self.assertEqual(self.codes(), ["vasp"])

    def test_aims_with_librpa(self):
        _touch(self.tmpdir, "control.in", "geometry.in", "librpa.out")
        (self.tmpdir / "run.out").write_text("  Invoking FHI-aims ...\n")
        results = detect_codes(self.tmpdir)
        self.assertEqual([r.code for r in results], ["aims", "librpa"])
        self.assertIn("run.out [Invoking FHI-aims]", results[0].evidences)

    def test_aims_output_only(self):
        (self.tmpdir / "Si.pgw.out").write_text("  Invoking FHI-aims ...\n")
        self.assertEqual(self.codes(), ["aims"])

    def test_w2k(self):
        _touch(self.tmpdir, "Si.struct", "Si.in1", "Si.klist")
        self.assertEqual(self.codes(), ["w2k"])

    def test_qe(self):
        (self.tmpdir / "scf.in").write_text("&CONTROL\n  calculation = 'scf'\n/\n")
        self.assertEqual(self.codes(), ["qe"])

    def test_abacus(self):
        _touch(self.tmpdir, "STRU", "OUT.ABACUS/")
        (self.tmpdir / "INPUT").write_text("INPUT_PARAMETERS\ncalculation scf\n")
        self.assertEqual(self.codes(), ["abacus"])

    def test_dir_pattern_not_match_file(self):
        """librpa.d/ should only match a directory"""
        _touch(self.tmpdir, "librpa.d")
        self.assertEqual(self.codes(), [])

    def test_single_weak_file_not_detected(self):
        _touch(self.tmpdir, "POSCAR")
        self.assertEqual(self.codes(), [])


if __name__ == "__main__":
    ut.main()
