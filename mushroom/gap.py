# -*- coding: utf-8 -*-
"""utilities related to GAP2 code"""
import struct
import numpy as np
from mushroom.core.logger import create_logger
from mushroom.core.typehint import Path

_logger = create_logger("gap")
del create_logger

class Eps:
    """object to handle the file ``.esp`` storing dielectric matrix

    Args:
        peps (Path): path to the epsilon binary file
        is_q0 (bool)
    """
    known_kind = ("eps", "inv", "invm1")

    def __init__(self, peps: Path, is_q0: bool = False, kind: str = "eps"):
        self._peps = peps
        self._rawdata = {}
        self._is_q0 = is_q0
        self._check_kind(kind)
        self._kind = kind
        with open(peps, 'rb') as h:
            self._msize = struct.unpack('i', h.read(4))[0]
            self._msize += int(is_q0)
        self.nrecl = 4
        # including the index of omega (integer, starting from 1)
        self._blk_iomega = 4 + 16 * self._msize ** 2
        self._nomega = 0
        with open(peps, 'rb') as h:
            while True:
                h.seek(self._seek_recl(self._nomega))
                data = h.read(1)
                if not data:
                    break
                self._nomega += 1

    @classmethod
    def _check_kind(cls, kind):
        if kind not in cls.known_kind:
            raise ValueError("unknown kind for .eps file: {}".format(kind))

    @property
    def is_q0(self):
        """if q=0"""
        return self._is_q0

    @property
    def kind(self):
        """the kind of data"""
        return self._kind

    @property
    def nomega(self):
        """number of frequency points"""
        return self._nomega

    @property
    def msize(self):
        """matrix size of the dielectric matrix in v-diagonal basis, including the head"""
        return self._msize

    def _seek_recl(self, iomega: int):
        """seek the location of the starting of matrix elements of eps(iomega)

        Args:
            iomega (int): index of frequency
        """
        return self.nrecl * self._blk_iomega * iomega

    def get(self, iomega: int, cache: bool = True):
        """get the raw eps data at frequency point iomega

        Args:
            iomega (int)
            cache (bool)
        """
        rawdata = self._rawdata.get(iomega, None)
        if cache and rawdata is not None:
            return rawdata
        with open(self._peps, 'rb') as h:
            h.seek(self._seek_recl(iomega))
            # first is an integer for matrix size
            struct.unpack('=i', h.read(4))
            counts = 2 * self._msize**2
            rawdata = np.frombuffer(h.read(8*counts),
                                    dtype='float64', count=counts)
            # reshape for head and wing
            rawdata = self._reshape(rawdata)
        if cache:
            self._rawdata[iomega] = rawdata
        return rawdata

    def _reshape(self, rawdata):
        rawdata = rawdata[0::2] + rawdata[1::2] * 1.0j
        reshaped = np.zeros((self.msize, self.msize), dtype='complex64')
        s = int(self._is_q0)
        reshaped[s:, s:] = rawdata[s*(2*self.msize-s):].reshape((self.msize-s, self.msize-s),
                                                                order='F')
        if s:
            reshaped[0, 0] = rawdata[0]
            # vertical wing
            reshaped[1:, 0] = rawdata[1:self.msize]
            # horizontal wing
            reshaped[0, 1:] = rawdata[self.msize:2*self.msize-1]
        return reshaped

    def get_eps(self, iomega: int, cache: bool = False):
        """get the dielectric matrix elements at frequency point iomega

        Args:
            iomega (int)
            cache (bool)
        """
        rawdata = self.get(iomega, cache=cache)
        if self._kind == "inv":
            eps = np.linalg.inv(rawdata)
        elif self._kind == "invm1":
            eps = np.linalg.inv(rawdata+np.diag([1.0+0.0j,]*self.msize))
        elif self._kind == "eps":
            eps = rawdata
        return eps

