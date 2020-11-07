# -*- coding: utf-8 -*-
"""define some public type hints"""
from os import PathLike
from numbers import Real, Complex
from typing import Tuple, Union, Sequence

# path
Path = Union[str, PathLike]
# string or int identifier for key
Key = Union[str, int]

# Vectors
# N-dimensional real vector
RealVec = Sequence[Real]
CplxVec = Sequence[Complex]
RealVec3D = Tuple[Real, Real, Real]
CplxVec3D = Tuple[Complex, Complex, Complex]
Latt3T3 = Tuple[RealVec3D, RealVec3D, RealVec3D]
del PathLike, Real, Tuple, Union, Sequence, Complex

