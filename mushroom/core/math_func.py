# -*- coding: utf-8 -*-
"""math functions"""
from typing import Sequence
import numpy as np
from scipy import special
from mushroom.core.typehint import RealVec3D

def solid_angle(xyz: Sequence[RealVec3D], polar_positive=True):
    """compute the solid angles from Cartisian coordinates

    use numpy.angle function

    Args:
        xyz (array-like,(n,3)): Cartisian coordinates
        polar_positive (bool): if True, the polar angle will fall in [0, pi].
            Otherwise [-pi/2,pi/2]

    Returns:
        Polar angle, theta, (n,) array
        Azimuthal angle, phi, (n,) array
    """
    xyz = np.array(xyz)
    shape = xyz.shape
    if len(shape) != 2 or shape[1] != 3:
        raise TypeError("invalid shape of Cartisian: {}".format(shape))
    xy = xyz[:, 0] + 1.0j * xyz[:, 1]
    r = np.absolute(xy)
    phi = np.angle(xy)
    theta = np.angle(r + xyz[:, 2] * 1.0j)
    if polar_positive:
        theta += np.pi / 2.0
    return theta, phi

def sph_harm(l: Sequence[int], m: Sequence[int], theta: Sequence[float], phi: Sequence[float]):
    """wrapper of scipy.special.sph_harm

    Args:
        l,m (int): angular and azimuthal angular momentum quanta
        theta, phi (array): polar and azimuthal angles
    """
    return special.sph_harm(m, l, phi, theta)

def sph_harm_xyz(l: Sequence[int], m: Sequence[int], xyz: Sequence[RealVec3D]):
    """compute spherical harmonics with Cartisian coordiantes

    Args:
        xyz (array-like,(n,3)): Cartisian coordinates
        theta, phi (array): polar and azimuthal angles
    """
    theta, phi = solid_angle(xyz, polar_positive=True)
    return sph_harm(l, m, theta, phi)

