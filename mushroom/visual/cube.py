# -*- coding: utf-8 -*-
"""facilities related to Gaussian Cube format"""
from typing import Sequence, Tuple, Union
from numbers import Real
from itertools import product

import numpy as np

from mushroom.core.logger import create_logger
from mushroom.core.elements import get_atomic_number
from mushroom.core.typing import RealVec3D, Latt3T3, Key, Path

_logger = create_logger('cube')
del create_logger

class Cube:
    """object for reading/writing Gaussian Cube file

    Args:
        data (ndarray, (n1,n2,n3)) : data with x, y, z coordiantes as outer, middle and inner loop
        voxel_vecs (ndarray, (3,3)) : step vector between voxels
    """
    default_comment = "Cube from mushroom"

    def __init__(self, data, voxel_vecs: Latt3T3, atms: Sequence[Key],
                 posi: Sequence[RealVec3D], origin: RealVec3D = [0., 0., 0.],
                 charges: Sequence[float] = None, comment: str = None):
        self.data = np.array(data)
        self.nvoxels = np.shape(data)
        self.voxel_vecs = np.array(voxel_vecs)
        self.atms = list(get_atomic_number(a) for a in atms)
        self.origin = origin
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
            self.comment =Cube.default_comment

    @property
    def N(self):
        """number of data point"""
        return len(self.atms)

    @property
    def size(self):
        """size of data, (x, y, z)"""
        return self.nvoxels

    def __eq__(self, o) -> bool:
        return np.array_equal(self.data, o.data)

    def export(self) -> str:
        """export cube data to a string"""
        slist = [self.comment,
                 "OUTER LOOP: X, MIDDLE LOOP: Y, INNER LOOP: Z",
                 "{:4d}{:12.6f}{:12.6f}{:12.6f}".format(len(self.atms), *self.origin),]
        for i in range(3):
            slist.append("{:4d}{:12.6f}{:12.6f}{:12.6f}"
                         .format(self.nvoxels[i], *self.voxel_vecs[i, :]))
        # atomic positions
        for an, c, posi in zip(self.atms, self.charges, self.posi):
            slist.append("{:4d}{:12.6f}{:12.6f}{:12.6f}{:12.6f}".format(an, c, *posi))
        data = self.data.flatten()
        nlines = len(data) // 6
        form = "{:13.5e}" * 6
        for i in range(nlines):
            slist.append(form.format(*data[6*i:6*(i+1)]))
        left = len(data) - nlines*6
        if left != 0:
            form = "{:13.5e}" * left
            slist.append(form.format(*data[-left:]))
        return "\n".join(slist)

    @classmethod
    def read(self, pcube: Path):
        """read a Cube file
        
        Args:
            pcube (str or PathLike): the path to the Cube file
        """
        raise NotImplementedError

