# -*- coding: utf-8 -*-
"""define some public type hints"""
from io import StringIO, TextIOWrapper
from os import PathLike
from numbers import Real, Complex
from typing import Tuple, Union, Sequence

# path
Path = Union[str, PathLike]
# string or int identifier for key
Key = Union[str, int]
TextIO = Union[str, PathLike, StringIO, TextIOWrapper]

# Vectors
# N-dimensional real vector
RealVec = Sequence[Real]
CplxVec = Sequence[Complex]
IntVec3D = Tuple[int, int, int]
RealVec3D = Tuple[Real, Real, Real]
CplxVec3D = Tuple[Complex, Complex, Complex]
Latt3T3 = Tuple[RealVec3D, RealVec3D, RealVec3D]
del PathLike, Real, Tuple, Union, Sequence, Complex, StringIO, TextIOWrapper

