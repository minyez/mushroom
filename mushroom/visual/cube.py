# -*- coding: utf-8 -*-
"""facilities related to Gaussian Cube format"""
from typing import Sequence
import numpy as np

from mushroom.core.logger import create_logger
from mushroom.core.elements import get_atomic_number
from mushroom.core.unit import LengthUnit
from mushroom.core.typehint import RealVec3D, Latt3T3, Key, TextIO

_logger = create_logger('cube')
del create_logger


class Cube(LengthUnit):
    """object for reading/writing Gaussian Cube file

    Args:
        data (ndarray, (n1,n2,n3)) : volumetric data
            x, y, z coordiantes as outer, middle and inner loop
        voxel_vecs (ndarray, (3,3)) : step vector between voxels
        posi (ndarray) : Cartisian coordinates of atoms
        atms (int/str sequence): atomic number or symbol of atoms
        charges (float sequence): charge of atoms
        origin (ndarray, (3,)): origin of the voxels
        unit (str): unit of input
        comment (str): comment information
    """
    default_comment = "Cube from mushroom"

    def __init__(self, data, voxel_vecs: Latt3T3, atms: Sequence[Key],
                 posi: Sequence[RealVec3D], origin: RealVec3D = None,
                 charges: Sequence[float] = None, comment: str = None,
                 unit="bohr"):
        LengthUnit.__init__(self, lunit=unit)
        self.data = np.array(data)
        self.voxel_vecs = np.array(voxel_vecs)
        self.posi = np.array(posi)
        self.atms = list(get_atomic_number(a) for a in atms)
        self.origin = origin
        if origin is None:
            self.origin = [0., 0., 0.]
        if len(atms) != len(posi):
            raise ValueError("Inconsistent length of atms and posi")
        if charges is None:
            self.charges = np.zeros(self.N)
        else:
            if len(charges) != self.N:
                raise ValueError("Inconsistent length of atms and charge")
            self.charges = charges
        self.comment = "{}".format(comment)
        if comment is None:
            self.comment = Cube.default_comment

    @property
    def unit(self):
        """length unit of lattice vectors and positions"""
        return self._lunit

    @unit.setter
    def unit(self, u):
        coef = self._get_lunit_conversion(u)
        if coef != 1:
            self.data = self.data / (coef ** 3)
            self.posi = self.posi * coef
            self.voxel_vecs = self.voxel_vecs * coef
            self._lunit = u.lower()

    @property
    def N(self):
        """number of data point"""
        return len(self.atms)

    @property
    def shape(self):
        """shape of data, (x, y, z)"""
        return np.shape(self.data)

    @property
    def nvoxels(self):
        """alias of shape"""
        return self.shape

    def __eq__(self, o) -> bool:
        return np.array_equal(self.data, o.data)

    def export(self) -> str:
        """export cube data to a string"""
        slist = [self.comment,
                 "OUTER LOOP: X, MIDDLE LOOP: Y, INNER LOOP: Z",
                 "{:4d}{:12.6f}{:12.6f}{:12.6f}"
                 .format(len(self.atms), *self.origin),]
        # convert to Bohr unit
        self.unit = "bohr"
        for i in range(3):
            slist.append("{:4d}{:12.6f}{:12.6f}{:12.6f}"
                         .format(self.nvoxels[i], *self.voxel_vecs[i, :]))
        # atomic positions
        for an, c, posi in zip(self.atms, self.charges, self.posi):
            slist.append("{:4d}{:12.6f}{:12.6f}{:12.6f}{:12.6f}"
                         .format(an, c, *posi))
        data = self.data.flatten()
        nlines = len(data) // 6
        form = "{:13.5E}" * 6
        for i in range(nlines):
            slist.append(form.format(*data[6 * i:6 * (i + 1)]))
        left = len(data) - nlines * 6
        if left != 0:
            form = "{:13.5E}" * left
            slist.append(form.format(*data[-left:]))
        return "\n".join(slist)

    @classmethod
    def read(cls, pcube: TextIO):
        """read a Cube file

        Args:
            pcube (TextIO): the TextIO object to write the Cube file
        """
        raise NotImplementedError
