#!/usr/bin/env python
# -*- coding: utf-8 -*-
# pylint: disable=C0116
"""test io utitlies"""
from io import StringIO
import os
import unittest as ut

from mushroom.core.ioutils import (split_comma, decode_int_range, decode_float_ends, grep,
                                   get_dirpath, get_file_ext, get_filename_wo_ext,
                                   get_cwd_name, get_matched_files, trim_after,# trim_comment,
                                   trim_before, trim_both_sides, conv_string,
                                   readtext_split_emptyline,
                                   cycler)

class test_string_decoding(ut.TestCase):
    """string decoding"""
    def test_decode_float_ends(self):
        """ends as two float numbers"""
        self.assertTupleEqual(decode_float_ends("-8.0~1"), (-8.0, 1.0))
        self.assertTupleEqual(decode_float_ends("m8.0~1"), (-8.0, 1.0))
        self.assertTupleEqual(decode_float_ends("-8.0~"), (-8.0, None))
        self.assertTupleEqual(decode_float_ends("~1"), (None, 1.0))
        self.assertTupleEqual(decode_float_ends("~"), (None, None))
        self.assertRaises(ValueError, decode_float_ends, "-8.0")
        self.assertRaises(ValueError, decode_float_ends, "m8.0~1", m_minus=False)

    def test_decode_int_range(self):
        self.assertListEqual(decode_int_range("5~9"), [5, 6, 7, 8, 9])
        self.assertListEqual(decode_int_range("vbm+5~+6"),
                             ["vbm+5", "vbm+6"])
        self.assertListEqual(decode_int_range("cbm-1~+2"),
                             ["cbm-1", "cbm+0", "cbm+1", "cbm+2"])

    def test_split_comma(self):
        self.assertListEqual(split_comma("5,6,9"), ["5", "6", "9"])
        self.assertListEqual(split_comma("2,6,9", int), [2, 6, 9])
        self.assertListEqual(split_comma("2,abc,9", int), [2, "abc", 9])
        self.assertListEqual(split_comma("a-2~1,9", int),
                             ["a-2", "a-1", "a+0", "a+1", 9])

    def test_conv_string(self):
        string = "1; ABC=5. "
        # unsupported conversion type
        self.assertRaises(AssertionError, conv_string, string, list, 0)
        # single value
        self.assertEqual(1, conv_string(string, int, 0, strips=";"))
        # multiple values
        self.assertListEqual([1, 5], conv_string(string, int, 0, 2, sep=r"[;=]", strips="."))


class test_grep(ut.TestCase):
    """test grep emulation"""
    def test_raise(self):
        """raise for bad filename and wrong type"""
        self.assertRaises(FileNotFoundError, grep, "test", "this_is_a_fake_file.extext",
                          error_not_found=True)
        self.assertRaises(TypeError, grep, "test", 1, error_not_found=True)

    def test_return_text(self):
        """match text"""
        s = StringIO("unittest\nutut\nut")
        self.assertListEqual(["utut\n", "ut",], grep("ut", s))
        s = ["unittest\n", "utut\n", "ut"]
        self.assertListEqual(["utut\n", "ut",], grep("ut", s))
        self.assertListEqual(["utut\n",], grep("ut", s, maxcounts=1))

    def test_return_lineum(self):
        """match text"""
        s = StringIO("unittest\nutut\nut")
        matched, index = grep("ut", s, return_linenum=True)
        self.assertListEqual(["utut\n", "ut",], matched)
        self.assertListEqual([1, 2], index)

    def test_group(self):
        """match text"""
        s = StringIO("unittest\nutut\nut")
        matched, index = grep("ut", s, return_group=True, return_linenum=True)
        self.assertListEqual(["ut", "ut",], [g.group() for g in matched])
        self.assertListEqual([1, 2], index)

    def test_from_behind(self):
        """match text"""
        s = StringIO("unittest\nutut\nut")
        matched, index = grep("ut", s, from_behind=True, return_linenum=True)
        self.assertListEqual(["ut", "utut\n"], matched)
        self.assertListEqual([2, 1], index)
        # check iterable stays the same
        s = ["unittest\n", "utut\n", "ut"]
        matched = grep("ut", s, from_behind=True)
        self.assertListEqual(s, ["unittest\n", "utut\n", "ut"])

    def test_maxdepth_counts(self):
        """match text"""
        s = StringIO("unittest\nutut\nut")
        matched = grep("ut", s, maxcounts=1)
        self.assertListEqual(["utut\n",], matched)
        matched = grep("ut", s, maxdepth=1)
        self.assertListEqual([], matched)

class test_trim(ut.TestCase):
    """string trimming functions"""
    def test_trim_before(self):
        """trim before"""
        self.assertEqual("defg", trim_before("abc#defg", r'#'))
        self.assertEqual("#defg", trim_before("abc#defg", r'#', include_pattern=True))
        self.assertEqual("comment", trim_before("I have Fortran!comment", r'!'))
        self.assertEqual("!comment", \
            trim_before("I have Fortran!comment", r'!', include_pattern=True))
        self.assertEqual("P", trim_before("Fe1P", r'\d'))
        self.assertEqual("1P", trim_before("Fe1P", r'\d', include_pattern=True))
        self.assertEqual("Fe", trim_before("Cd2Fe", r'\d'))
        self.assertEqual("2Fe", trim_before("Cd2Fe", r'\d', include_pattern=True))

    def test_trim_after(self):
        """trim after"""
        self.assertEqual("abc", trim_after("abc#defg", r'#'))
        self.assertEqual("abc#", trim_after("abc#defg", r'#', include_pattern=True))
        self.assertEqual("I have Fortran", \
            trim_after("I have Fortran!comment", r'!'))
        self.assertEqual("I have Fortran!", \
            trim_after("I have Fortran!comment", r'!', include_pattern=True))
        self.assertEqual("Fe", trim_after("Fe1", r'\d'))
        self.assertEqual("Cd2", trim_after("Cd2Fe", r'\d', include_pattern=True))

    def test_trim_both_sides(self):
        """trim both"""
        string = "WFFIL  EF=0.9725 (WFFIL, WFPRI, ENFIL, SUPWF)"
        self.assertEqual("0.9725 ", \
            trim_both_sides(string, r"=", r"\("))
        self.assertEqual("=0.9725 (", \
            trim_both_sides(string, r"=", r"\(", include_pattern=True))


class test_textio_operations(ut.TestCase):
    """test textio"""
    def test_readtext_split_emptyline(self):
        """test readtext"""
        tests = (
            ("abc\n\ndef\n\nghi", 3, ["abc\n", "def\n", "ghi"]),
            ("\n\nabc\n\ndef\n\nghi \n", 3, ["abc\n", "def\n", "ghi \n"]),
            ("\n\nabc\n\ndef\n \n", 2, ["abc\n", "def\n"]),
            ("\n\nabc\ncba\n\ndef\n \n", 2, ["abc\ncba\n", "def\n"]),
            )
        for s, n, correct in tests:
            strings = readtext_split_emptyline(StringIO(s))
            self.assertEqual(len(strings), n)
            self.assertListEqual(strings, correct)


class test_file_path(ut.TestCase):
    """test of utilities related to file and path"""
    def test_get_cwd_name(self):
        """get cwd name"""
        try:
            os.chdir(os.path.dirname(__file__))
        except FileNotFoundError:
            pass
        self.assertEqual("test", get_cwd_name())

    def test_dirpath(self):
        """get dirpath"""
        self.assertEqual("test", os.path.basename(get_dirpath(__file__)))
        self.assertEqual("/home/user/abc", get_dirpath("/home/user/abc/efg"))
        self.assertEqual("/bin", get_dirpath("/bin"))

    def test_file_ext(self):
        """get file extension"""
        self.assertEqual("", get_file_ext("noext"))
        self.assertEqual("py", get_file_ext(__file__))
        self.assertEqual("txt", get_file_ext("/home/user/abc.txt"))
        self.assertEqual("in", get_file_ext("/home/user/abc.abi.in"))
        # non-greedy
        self.assertEqual("", get_file_ext("noext", greedy=False))
        self.assertEqual("py", get_file_ext(__file__, greedy=False))
        self.assertEqual("txt", get_file_ext("/home/user/abc.txt", greedy=False))
        self.assertEqual("abi.in", get_file_ext("/home/user/abc.abi.in", greedy=False))

    def test_filename_wo_ext(self):
        """get file extension"""
        self.assertEqual("test_ioutils", get_filename_wo_ext(__file__))
        self.assertEqual("abc", get_filename_wo_ext("/home/user/abc.txt"))

    def test_get_matched_files(self):
        """get match files"""
        try:
            os.chdir(os.path.dirname(__file__))
        except FileNotFoundError:
            pass
        self.assertTupleEqual(("test_ioutils.py",),
                              get_matched_files(regex=r".*ioutils.*", relative=True))

class test_number(ut.TestCase):
    """test number related utilities"""
    def test_cycler(self):
        lt = ["abc", "def", "123"]
        self.assertEqual(0, cycler(len(lt), lt, return_int=True))
        self.assertEqual("def", cycler(len(lt)+1, lt))

#   trim_comment,

if __name__ == "__main__":
    ut.main()

