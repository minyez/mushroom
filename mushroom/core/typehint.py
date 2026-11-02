# -*- coding: utf-8 -*-
"""define some public type hints"""
from io import StringIO, TextIOWrapper
from os import PathLike
from numbers import Real, Complex
from typing import Union
from collections.abc import Sequence

# path
Path = Union[str, PathLike]
# string or int identifier for key
Key = Union[str, int]
TextIO = Union[str, PathLike, StringIO, TextIOWrapper]

# Vectors
# N-dimensional real vector
RealVec = Sequence[Real]
CplxVec = Sequence[Complex]
IntVec3D = tuple[int, int, int]
RealVec3D = tuple[Real, Real, Real]
CplxVec3D = tuple[Complex, Complex, Complex]
Latt3T3 = tuple[RealVec3D, RealVec3D, RealVec3D]

del PathLike, Real, Union, Sequence, Complex, StringIO, TextIOWrapper
