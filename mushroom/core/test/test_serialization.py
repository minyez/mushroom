"""Round trips through portable, pickle-free archives."""
import json
import tempfile
import unittest as ut
from pathlib import Path
from zipfile import ZipFile
import numpy as np
from mushroom.core.bs import BandStructure, BandPathData, random_band_structure
from mushroom.core.dos import DensityOfStates
from mushroom.core.serialization import save_npz


class test_serialization(ut.TestCase):

    def test_bands(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bands.npz"
            for nspin in (1, 2):
                for proj in (False, True):
                    for occupied in (False, True):
                        bs = random_band_structure(nspins=nspin, nkpts=3, nbands=4,
                                                   has_proj=proj)
                        if not occupied:
                            bs = BandStructure(bs.eigen, efermi=bs.vbm, pwav=bs.pwav,
                                               atms=bs.atms, prjs=bs.prjs)
                        bs.save(path)
                        new = BandStructure.load(path)
                        for key in ('eigen', 'occ', 'weight', 'pwav'):
                            np.testing.assert_equal(getattr(new, key), getattr(bs, key))
                        for key in ('efermi', 'unit', 'vbm', 'cbm'):
                            self.assertEqual(getattr(new, key), getattr(bs, key))
                        self.assertEqual(new.fund_gap(), bs.fund_gap())
                        with ZipFile(path) as archive:
                            self.assertTrue(all(s.endswith('.npy') for s in archive.namelist()))
                        with np.load(path, allow_pickle=False) as archive:
                            for key in archive.files:
                                self.assertFalse(archive[key].dtype.hasobject)
            bs = BandStructure([[[-1, 2], [-2, 3]]])
            bs.save(path)
            self.assertIsNone(BandStructure.load(path).occ)
            with self.assertRaisesRegex(ValueError, "BandStructure"):
                DensityOfStates.load(path)
            np.savez(path, __meta__=json.dumps(dict(format='mushroom', format_version=2,
                                                  kind='BandStructure')))
            with self.assertRaisesRegex(ValueError, "version=2"):
                BandStructure.load(path)
            with self.assertRaisesRegex(ValueError, "Object"):
                save_npz(path, 'test', {'array': [None]}, ['array'])

    def test_dos_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'data.npz'
            for projected in (False, True):
                dos = DensityOfStates([-1, 0, 1], [[2, 3, 2]], efermi=0.5,
                                      pdos=np.ones((1, 3, 1, 1)) if projected else None,
                                      atms=['Si'], prjs=['s'])
                dos.save(path)
                new = DensityOfStates.load(path)
                for key, val in dos.to_dict().items():
                    np.testing.assert_equal(new.to_dict()[key], val)
            bs = BandStructure([[[-1, 2], [-2, 3]]], efermi=0.)
            for lattice in (None, np.eye(3)):
                data = BandPathData(bs, np.array([[0, 0, 0], [0.5, 0, 0]]), lattice,
                                    ['Gamma', 'X'], 'test', 'input')
                data.save(path)
                new = BandPathData.load(path)
                np.testing.assert_equal(new.kpts, data.kpts)
                np.testing.assert_equal(new.recp_latt, lattice)
                self.assertEqual(new.ksymbols, data.ksymbols)
                self.assertEqual(new.code, 'test')
                self.assertEqual(new.source, 'input')
                np.testing.assert_equal(new.kpath().x, [0, .5])
                np.testing.assert_equal(new.kpath(True).x, [0, 1])
