"""binary reader tests with independently constructed records"""
from pathlib import Path
import struct
import tempfile
import unittest as ut

import numpy as np

from mushroom import librpa
from mushroom.aims.gw import read_aims_self_energy_restart_file
from mushroom.io import read_elsi_to_csc


class test_binary_readers(ut.TestCase):
    def test_elsi_real_and_complex(self):
        # Columns [1,0,2], [0,3,0], [4,0,5], using Fortran's one-based indices.
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / 'matrix.csc'
            for complex_ in [False, True]:
                header = [0] * 16
                header[2], header[3], header[5] = int(complex_), 3, 5
                values = [1, 2, 3, 4, 5] if not complex_ else [1, -1, 2, -2, 3, -3, 4, -4, 5, -5]
                data = (struct.pack('<16q', *header) + struct.pack('<3q', 1, 3, 4)
                        + struct.pack('<5i', 1, 3, 2, 1, 3) + struct.pack(f'<{len(values)}d', *values))
                p.write_bytes(data)
                result = read_elsi_to_csc(p, verbose=True)
                expected = np.array([[1, 0, 4], [0, 3, 0], [2, 0, 5]]) * (1 - 1j if complex_ else 1)
                np.testing.assert_array_equal(result.toarray(), expected)
                result.data[0] = 7
                self.assertEqual(result[0, 0], 7)
                p.write_bytes(data[:-1])
                with self.assertRaises(ValueError):
                    read_elsi_to_csc(p)
            p.write_bytes(b'')
            with self.assertRaises(ValueError):
                read_elsi_to_csc(p)

    def test_band_eigenvectors_and_soc(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / 'eigenvectors'
            data = struct.pack('=16d', *range(16))
            p.write_bytes(data)
            expected = np.array([[[0+1j, 2+3j, 4+5j, 6+7j], [8+9j, 10+11j, 12+13j, 14+15j]]])
            np.testing.assert_array_equal(librpa.read_band_eigenvector(p, 4, 2, 1), expected)
            np.testing.assert_array_equal(librpa.read_band_eigenvector(p, 4, 2, 1, True), expected[:, :, [0, 2, 1, 3]])
            with self.assertRaises(ValueError):
                librpa.read_band_eigenvector(p, 2, 2, 2, True)
            p.write_bytes(data[:-1])
            with self.assertRaises(ValueError):
                librpa.read_band_eigenvector(p, 4, 2, 1)

    def test_aims_restart_layout(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / 'self_energy_grid.dat'
            # One spin, two k-points, two states and two frequencies; frequency varies fastest.
            content = struct.pack('=4i2d16d', 1, 2, 2, 2, 0.5, 1.5, *range(16))
            p.write_bytes(content)
            omega, sigma = read_aims_self_energy_restart_file(p)
            np.testing.assert_array_equal(omega, [0.5, 1.5])
            np.testing.assert_array_equal(sigma, [[[[0+1j, 2+3j], [4+5j, 6+7j]],
                                                  [[8+9j, 10+11j], [12+13j, 14+15j]]]])
            omega[0] = 2
            sigma[0, 0, 0, 0] = 3
            p.write_bytes(content[:-1])
            with self.assertRaises(ValueError):
                read_aims_self_energy_restart_file(p)

    def test_momentum_reader_explicitly_unimplemented(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / 'momentum'
            p.write_bytes(struct.pack('=6i', 1, 1, 2, 3, 1, 3))
            with self.assertRaises(NotImplementedError):
                librpa.read_moment_KS_aims(p)


class test_binary_handle_lifetime(ut.TestCase):
    def test_eps_context_closes_on_exception(self):
        from mushroom.gap import Eps
        path = Path(__file__).parent / 'data/diamond.eps-q2'
        with self.assertRaisesRegex(RuntimeError, 'test'):
            with Eps(path, kind='invm1', cache=True) as eps:
                data = eps.get(0)
                handle = eps._fhandle
                self.assertFalse(handle.closed)
                raise RuntimeError('test')
        self.assertTrue(handle.closed)
        self.assertIs(eps.get(0), data)
        eps.close()

    def test_wavecar_context_closes(self):
        from mushroom.vasp import WaveCar
        # A single k-point and band, two complex64 coefficients; 128-byte direct-access records.
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)/'WAVECAR'
            data = bytearray(512)
            struct.pack_into('=3d', data, 0, 128, 1, 45200)
            struct.pack_into('=12d', data, 128, 1, 1, 10, 1,0,0,0,1,0,0,0,1)
            struct.pack_into('=6d', data, 256, 2,0,0,0,-1,1)
            struct.pack_into('=4f', data, 384, 1,2,3,4)
            p.write_bytes(data)
            with WaveCar(p) as wave:
                coef = wave.get_raw_coeff(0,0,0)
                handle = wave._fhandle
                np.testing.assert_array_equal(coef,[1+2j,3+4j])
                self.assertEqual(wave.bs.eigen[0,0,0],-1)
                np.testing.assert_array_equal(wave.kpts,[[0,0,0]])
            self.assertTrue(handle.closed)
            wave.close()
