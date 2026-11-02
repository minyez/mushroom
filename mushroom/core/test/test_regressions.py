"""regressions for boundary cases in core readers and exporters"""
import contextlib
import io
import os
from pathlib import Path
import tempfile
import unittest as ut
from unittest.mock import patch

import numpy as np

from mushroom.core import ioutils as iu
from mushroom.core.cell import Cell
from mushroom.core.cif import CifBlk
from mushroom.core.elements import get_atomic_number, get_atomic_weight
from mushroom.core.pkg import detect, detect_matchhead, detect_matchtail


class test_ioutils_regressions(ut.TestCase):
    def test_fortran_booleans(self):
        self.assertEqual(iu.conv_string('F .FALSE. FALSE .F. T true', bool),
                         [False, False, False, False, True, True])

    def test_generator_and_group_zero(self):
        self.assertEqual(iu.grep(r'\d+', (x for x in ['a1\n', 'b2\n']), return_group=0), ['1', '2'])

    def test_reverse_line_numbers(self):
        self.assertEqual(iu.grep('x', iter(['x\n', 'a\n', 'x\n', 'x']),
                                 from_behind=True, maxdepth=2, return_linenum=True),
                         (['x', 'x\n'], [3, 2]))

    def test_binary_and_detection(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / 'unknown'
            p.write_bytes(b'\xff\x00\nabc\n')
            self.assertEqual(iu.grep(b'abc', p, is_binary=True), [b'abc\n'])
            self.assertIsNone(detect(p))
            self.assertIsNone(detect_matchhead(p))
            self.assertIsNone(detect_matchtail(p))

    def test_first_last_line_boundaries(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / 'text'
            for content, expected in [('', ('', '')), ('a', ('a', 'a')), ('a\n', ('a\n', 'a\n')),
                                      ('α\nβ', ('α\n', 'β')), ('a\nb\n', ('a\n', 'b\n'))]:
                with self.subTest(content=content):
                    p.write_text(content)
                    self.assertEqual(iu.get_first_last_line(p), expected)

    def test_first_last_line_only_decodes_two_lines(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / 'binary'
            p.write_bytes(b'first\n\xff\xfe\n' + b'x' * 5000 + b'\nlast\n')
            self.assertEqual(iu.get_first_last_line(p), ('first\n', 'last\n'))
            p.write_bytes(b'first\n' + b'y' * 5000 + b'\n')
            self.assertEqual(iu.get_first_last_line(p), ('first\n', 'y' * 5000 + '\n'))

    def test_filename_of_current_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            sub = Path(tmp).resolve() / 'case.d'
            sub.mkdir()
            cwd = os.getcwd()
            os.chdir(sub)
            try:
                self.assertEqual(iu.get_filename_wo_ext('.'), 'case')
                self.assertEqual(iu.get_filename_wo_ext('..'), Path(tmp).resolve().stem)
                self.assertEqual(iu.get_filename_wo_ext('.', dirname=True), str(sub.with_name('case')))
            finally:
                os.chdir(cwd)

    def test_disabled_minus(self):
        with self.assertRaises(ValueError):
            iu.decode_int_ends('1:m9', m_minus=False)

    def test_filename_and_files_outside_cwd(self):
        self.assertEqual(iu.get_filename_wo_ext('some/archive.tar.gz', dirname=True), 'some/archive.tar')
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)
            (p / 'sub').mkdir()
            (p / 'data').touch()
            self.assertEqual(iu.get_matched_files(dirpath=p), (str((p / 'data').resolve()),))
            self.assertEqual(iu.get_matched_files(dirpath=p, relative=True), (os.path.relpath((p / 'data').resolve()),))

    def test_redirected_stdout_and_borrowed_stream(self):
        stream = io.StringIO()
        with contextlib.redirect_stdout(stream):
            iu.print_file_or_iowrapper('hello')
            with iu.open_textio(stream, 'w') as handle:
                handle.write('world')
        self.assertFalse(stream.closed)
        self.assertEqual(stream.getvalue(), 'hello\nworld')
        with tempfile.TemporaryFile(mode='w+') as stream:
            with iu.open_textio(stream, 'w') as handle:
                handle.write('borrowed')
            self.assertFalse(stream.closed)


class test_cell_regressions(ut.TestCase):
    def test_error_messages_are_readable(self):
        c = Cell(np.eye(3), ['H'], [[0, 0, 0]])
        with self.assertRaisesRegex(ValueError, r'^Unsupported export: foo$'):
            c.export('foo')
        for factory in [Cell.rutile, Cell.anatase]:
            with self.assertRaisesRegex(Exception, 'should be in \\(0,1\\), get 1.5'):
                factory(u=1.5)

    def test_qe_units(self):
        for unit, label in [('ang', 'angstrom'), ('bohr', 'bohr')]:
            c = Cell(np.eye(3), ['H'], [[0, 0, 0]], unit=unit)
            self.assertIn('CELL_PARAMETERS ' + label, c.export_qe())

    def test_export_restores_state_on_error(self):
        for method in ['export_qe', 'export_qe_alat', 'export_abi', 'export_vasp', 'export_aims']:
            c = Cell(np.eye(3) * 2, ['H'], [[0.3, 0.4, 0.5]], unit='bohr', coord_sys='C')
            latt, posi = c.latt.copy(), c.posi.copy()
            with self.subTest(method=method):
                with patch.object(Cell, 'atom_types', new_callable=ut.mock.PropertyMock, side_effect=RuntimeError):
                    if method in ['export_qe', 'export_qe_alat']:
                        with self.assertRaises(RuntimeError):
                            getattr(c, method)()
                    else:
                        # Fail after the temporary representation change.
                        with patch('mushroom.core.cell.sym_nat_from_atms', side_effect=RuntimeError), \
                             patch.object(Cell, 'get_reference', side_effect=RuntimeError):
                            with self.assertRaises(RuntimeError):
                                getattr(c, method)()
                self.assertEqual((c.unit, c.coord_sys), ('bohr', 'C'))
                np.testing.assert_array_equal(c.latt, latt)
                np.testing.assert_array_equal(c.posi, posi)

    def test_cif_name(self):
        for name in ['data1', 'tiO2']:
            self.assertEqual(CifBlk.read(io.StringIO('data_' + name + '\n_tag value\n')).name, name)

    def test_atomic_number_bounds(self):
        for value in [-1, True, False, 119]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                get_atomic_number(value)
            with self.assertRaises(ValueError):
                get_atomic_weight(value)
        self.assertEqual(get_atomic_number(0), 0)
        self.assertEqual(get_atomic_number('Si'), 14)
