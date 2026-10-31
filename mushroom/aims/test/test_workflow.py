#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test utilities for FHI-aims workflows"""
import pathlib
import sys
import tempfile
import unittest as ut

from mushroom.aims.workflow import get_species_text, link_files, run_aims


class test_get_species_text(ut.TestCase):
    """test getting species defaults for a geometry"""

    def test_copy_without_change(self):
        """blocks are in the alphabetic order and keep their comments"""
        with tempfile.TemporaryDirectory() as tmpdir:
            top = pathlib.Path(tmpdir)
            directory = top / "defaults_2020" / "intermediate_gw"
            directory.mkdir(parents=True)
            (directory / "01_H_default").write_text("# comment of H\n  species H\n")
            (directory / "31_Ga_default").write_text("  species Ga\n#  hydro 4 f 9\n")
            (directory / "33_As_default").write_text("  species As\n")
            geometry = top / "geometry.in"
            geometry.write_text("atom_frac 0 0 0 Ga\natom_frac 0.25 0.25 0.25 As\n"
                                "lattice_vector 1 0 0\n")
            text = get_species_text(geometry, "defaults_2020/intermediate_gw",
                                    species_defaults=str(top))
        self.assertEqual(text, "  species As\n  species Ga\n#  hydro 4 f 9\n")


class test_link_files(ut.TestCase):
    """test linking files of a calculation"""

    def test_link(self):
        """matched files are linked, and old links are replaced"""
        with tempfile.TemporaryDirectory() as tmpdir:
            top = pathlib.Path(tmpdir)
            (top / "scf").mkdir()
            (top / "nscf").mkdir()
            (top / "scf" / "D_1.csc").write_text("1")
            (top / "scf" / "aims.out").write_text("out")
            (top / "nscf" / "D_1.csc").symlink_to(top / "scf" / "aims.out")
            links = link_files(top / "scf", top / "nscf", "D_*")
            self.assertListEqual([x.name for x in links], ["D_1.csc"])
            self.assertEqual((top / "nscf" / "D_1.csc").read_text(), "1")
            self.assertFalse((top / "nscf" / "aims.out").exists())

    def test_missing(self):
        """raise when restart files are not found"""
        with tempfile.TemporaryDirectory() as tmpdir:
            self.assertRaises(FileNotFoundError, link_files, tmpdir, tmpdir, "D_*")


class test_run_aims(ut.TestCase):
    """test running FHI-aims with a fake program"""
    code = "import sys; print('{}'); print('error', file=sys.stderr)"
    finished = r"  Self-consistency cycle converged.\n\n          Have a nice day.\n" \
        r"------------------------------------------------------------"

    def test_finished(self):
        """stdout and stderr are separated"""
        with tempfile.TemporaryDirectory() as tmpdir:
            run_aims([sys.executable, "-c", self.code.format(self.finished)], cwd=tmpdir)
            self.assertIn("Have a nice day", (pathlib.Path(tmpdir) / "aims.out").read_text())
            self.assertEqual((pathlib.Path(tmpdir) / "aims.err").read_text(), "error\n")

    def test_finished_without_scf(self):
        """a run with sc_iter_limit 0 ends without the nice-day line, and it is not converged"""
        ending = r"          Leaving FHI-aims.\n\n----"
        with tempfile.TemporaryDirectory() as tmpdir:
            command = [sys.executable, "-c", self.code.format(ending)]
            run_aims(command, cwd=tmpdir, require_converge=False)
            self.assertRaises(RuntimeError, run_aims, command, cwd=tmpdir)

    def test_not_finished(self):
        """a run with exit code 0 and no normal ending is caught"""
        with tempfile.TemporaryDirectory() as tmpdir:
            self.assertRaises(RuntimeError, run_aims,
                              [sys.executable, "-c", self.code.format("stopped")], cwd=tmpdir)


if __name__ == "__main__":
    ut.main()
