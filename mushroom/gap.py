# -*- coding: utf-8 -*-
"""utilities related to GAP2 code

TODO:
    check out the use of nbyte_recl
"""
import struct
import pathlib
import numpy as np
from mushroom.core.logger import create_logger
from mushroom.core.typehint import Path
from mushroom.core.bs import BandStructure
from mushroom.core.ioutils import conv_string
from mushroom.core.data import reshape_2n_float_n_cmplx

from mushroom.w2k import get_casename

_logger = create_logger("gap")
del create_logger

gwmethod_suffices = {'g0w0': 'GW', 'gw0': 'GW0'}

class Eps:
    """object to handle the file ``.eps`` storing dielectric matrix

    Args:
        peps (Path): path to the epsilon binary file
        is_q0 (bool)
        kind (str)
        nbyte_recl (int) : number of bytes as unit of record length. default to 4.
            Use 1 if GAP is compiled with ``assume bytenbyte_recl`` or compiled with gcc
    """
    known_kind = ("eps", "inv", "invm1")

    def __init__(self, peps: Path, is_q0: bool = False,
                 kind: str = "eps", nbyte_recl: int = 1):
        self._peps = peps
        self._fhandle = None
        self._rawdata = {}
        self._is_q0 = is_q0
        self._check_kind(kind)
        self._kind = kind
        with open(peps, 'rb') as h:
            self._msize = struct.unpack('i', h.read(4))[0]
            self._msize += int(is_q0)
        self._nbyte_recl = nbyte_recl
        # including the index of omega (integer, starting from 1)
        self._blk_iomega = 4 + 16 * self._msize ** 2
        self._nomega = 0
        with open(peps, 'rb') as h:
            while True:
                h.seek(self._seek_record(self._nomega))
                data = h.read(1)
                if not data:
                    break
                self._nomega += 1

    def close(self):
        """close the binary handle"""
        if self._fhandle is not None:
            self._fhandle.close()
            self._fhandle = None

    @classmethod
    def _check_kind(cls, kind):
        if kind not in cls.known_kind:
            raise ValueError("unknown kind for .eps file: {}".format(kind))

    @property
    def is_q0(self):
        """if q=0"""
        return self._is_q0

    @property
    def nbyte_recl(self):
        """record length"""
        return self._nbyte_recl

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

    def _seek_record(self, iomega: int):
        """seek the record location of the starting of matrix elements of eps(iomega)

        Args:
            iomega (int): index of frequency
        """
        return self._nbyte_recl * self._blk_iomega * iomega

    def get(self, iomega: int, cache: bool = True):
        """get the raw eps data at frequency point iomega

        Args:
            iomega (int)
            cache (bool)
        """
        rawdata = self._rawdata.get(iomega, None)
        if cache and rawdata is not None:
            return rawdata
        if self._fhandle is None:
            self._fhandle = open(self._peps, 'rb')
        self._fhandle.seek(self._seek_record(iomega))
        # first is an integer for matrix size
        struct.unpack('=i', self._fhandle.read(4))
        counts = 2 * self._msize**2
        rawdata = np.frombuffer(self._fhandle.read(8*counts),
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

class Eqpev:
    """quasiparticle data object"""
    _head_lines = 10
    # pylint: disable=R0914
    def __init__(self, peqpev: Path = None, dirpath: Path = ".",
                 casename: str = None, method: str = 'g0w0'):
        if casename is None:
            casename = get_casename(dirpath)
        dirpath = pathlib.Path(dirpath)
        if peqpev is None:
            try:
                peqpev = dirpath / "{}.eqpeV_{}".format(casename, gwmethod_suffices[method.lower()])
            except KeyError as err:
                raise KeyError("unknown gw method: {}".format(method)) from err
        else:
            suffix = str(peqpev).split('_')[-1]
            if suffix in gwmethod_suffices.values():
                for k, v in gwmethod_suffices.items():
                    if v == suffix:
                        method = k
                        break
            else:
                raise ValueError("fail to detect the method used in the file {}".format(peqpev))
        self._peqpev = peqpev
        self._method = method.lower()
        data = np.loadtxt(peqpev)
        nkpts = int(data[-1, 0])
        nbandsgw = int(data[-1, 1] - data[0, 1]) + 1
        self._ibandsgw = np.array(data[0:nbandsgw+1, 1], dtype='int')
        self._eks = np.reshape(data[:, 2], (1, nkpts, nbandsgw), order="C")
        self._eqp = np.reshape(data[:, 3], (1, nkpts, nbandsgw), order="C")
        self._ehf = np.reshape(data[:, 4], (1, nkpts, nbandsgw), order="C")
        self._degw = np.reshape(data[:, -4], (1, nkpts, nbandsgw), order="C")
        self._nbandsgw = nbandsgw
        # KS band structure
        self._ks_bs = None
        self._qp_bs = None
        self._hf_bs = None
        # get kpoints information (weight not included)
        with open(peqpev, 'r') as h:
            lines = h.readlines()
        self._ik = []
        self._ibzkpts = []
        for ik in range(nkpts):
            l = lines[self._head_lines+ik*(2+nbandsgw)]
            kpt = conv_string(l, int, 3, -5, -4, -3, -1)
            self._ibzkpts.append([x/kpt[-1] for x in kpt[1:4]])
            self._ik.append(kpt[0])
        self._ik = np.array(self._ik)
        self._ibzkpts = np.array(self._ibzkpts)

    @property
    def method(self) -> str:
        """method used to calculate this eps file"""
        return self._method

    @property
    def ibzkpts(self):
        """coordinates of irreducible kpoints"""
        return self._ibzkpts

    @property
    def nibzkpts(self) -> int:
        """coordinates of irreducible kpoints"""
        return len(self._ibzkpts)

    def _get_bandstructure(self, kind):
        e = {"qp": self._eqp, "ks": self._eks, "hf": self._ehf}
        assert kind in e
        e = e[kind]
        occ = 1.0 * (e < 0.009)
        weight = [1.0,] * self.nibzkpts
        return BandStructure(e, occ, weight, unit="ev", efermi=0.0)

    def get_KS_bandstructure(self):
        """get Kohn-Sham band structure"""
        if self._ks_bs is None:
            self._ks_bs = self._get_bandstructure("ks")
        return self._ks_bs

    def get_QP_bandstructure(self):
        """get quasi-particle band structure"""
        if self._qp_bs is None:
            self._qp_bs = self._get_bandstructure("qp")
        return self._qp_bs

    def get_HF_bandstructure(self):
        """get Hartree-Fock band structure"""
        if self._hf_bs is None:
            self._hf_bs = self._get_bandstructure("hf")
        return self._hf_bs

class Vmat:
    """analyze Coulomb matrix vmat binary data (2e-201117)"""
    def __init__(self, pvmat: Path, nbyte_recl: int = 4):
        self._pvmat = pvmat
        self._nbyte_recl = nbyte_recl
        self._iq = None
        self._vmat = None
        self._msize = None
        self._recl = None
        self._ev = None
        self._load()

    @property
    def nbyte_recl(self):
        """unit of record length"""
        return self._nbyte_recl

    @property
    def is_q0(self):
        """bool, if the object is matrix elements at q=0"""
        return self.iq == 1

    @property
    def ev(self):
        """eigenvalue"""
        if self._ev is None:
            self._ev = np.linalg.eigvalsh(self._vmat)
        return self._ev

    @property
    def diag(self):
        """diagonal elements"""
        return np.diagonal(self._vmat)

    @property
    def iq(self):
        """int, index of qpoint, starting from 1"""
        return self._iq

    @property
    def vmat(self):
        """complex ndarray, elements of Coulomb matrix"""
        return self._vmat

    @property
    def msize(self):
        """int, size of Coulomb matrix"""
        return self._msize

    @property
    def recl(self):
        """int, record length"""
        return self._recl

    def is_hermitian(self):
        """if the Coulomb matrix is Hermitian

        Returns:
            bool
        """
        diff = self._vmat - self._vmat.conjugate().T
        return np.allclose(diff, 0.0)

    def _load(self):
        """load the binary file"""
        with open(self._pvmat, 'rb') as h:
            recl, iq, msize = struct.unpack('iii', h.read(12))
            self._recl = recl
            self._iq = iq
            self._msize = msize
            h.seek(recl)
            vmat = []
            for i in range(msize):
                h.seek((1+i)*recl)
                data = np.frombuffer(h.read(16*msize), dtype='float64', count=2*msize)
                vmat.append(reshape_2n_float_n_cmplx(data))
            self._vmat = np.array(vmat)

