# -*- coding: utf-8 -*-
"""math functions"""
from numbers import Real, Number
from typing import Sequence, Tuple, Union

import numpy as np

from mushroom.core.constants import PI
from mushroom.core.typehint import RealVec3D
from mushroom.core.ioutils import raise_no_module


def solid_angle(xyz: Sequence[RealVec3D], polar_positive=True):
    """compute the solid angles from Cartisian coordinates

    use numpy.angle function

    Args:
        xyz (array-like, (,3) or (n,3)): Cartisian coordinates
        polar_positive (bool): if True, the polar angle will fall in [0, pi].
            Otherwise [-pi/2,pi/2]
            with 0 or -pi/2 corresponds to the positive z-axis

    Returns:
        Polar angle, theta, (n,) array
        Azimuthal angle, phi, (n,) array
    """
    xyz = np.array(xyz)
    shape = xyz.shape
    if len(shape) not in [1, 2] or shape[-1] != 3:
        raise TypeError("invalid shape of Cartisian: {}".format(shape))
    if len(shape) == 2:
        xy = xyz[:, 0] + 1.0j * xyz[:, 1]
        r = np.absolute(xy)
        theta = np.angle(r + xyz[:, 2] * 1.0j)
    else:
        xy = xyz[0] + 1.0j * xyz[1]
        r = np.absolute(xy)
        theta = -np.angle(r + xyz[2] * 1.0j)
    phi = np.angle(xy)
    if polar_positive:
        theta += np.pi / 2.0
    return theta, phi


def sph_harm(l: Sequence[int], m: Sequence[int], theta: Sequence[float], phi: Sequence[float]):
    """wrapper of scipy.special.sph_harm_y

    Args:
        l,m (int): angular and azimuthal angular momentum quanta
        theta, phi (array): polar and azimuthal angles
    """
    from scipy import special
    return special.sph_harm_y(l, m, theta, phi)


def sph_harm_xyz(l: Sequence[int], m: Sequence[int], xyz: Sequence[RealVec3D]):
    """compute spherical harmonics with Cartisian coordiantes

    Args:
        xyz (array-like,(n,3)): Cartisian coordinates
        theta, phi (array): polar and azimuthal angles
    """
    theta, phi = solid_angle(xyz, polar_positive=True)
    return sph_harm(l, m, theta, phi)


def rising_factor(N: Real, k: Real):
    """compute rising factor by Gamma function

    The rising factor is defined as

    (N)_k = Gamma(N+k)/Gamma(N)

    Args:
        N, k (Real)
    """
    from scipy import special
    return special.gamma(np.add(N, k)) / special.gamma(N)


def gamma_negahalf(n):
    """compute gamma function at negative half integer, Gamma(1/2-n)"""
    g = np.sqrt(np.pi) * (-2)**n
    for i in range(n):
        g /= 2 * i + 1
    return g


def general_comb(N: Real, k: Real):
    """comupte a general combination number by Gamma function and rising factor

    The combintation number C(N, k) is defined as
        C(N, k) = N!/k!/(N-k)! = rising_factor(N-k+1, k)/Gamma(k+1)
    """
    from scipy import special
    return rising_factor(np.subtract(N, k) + 1, k) / special.gamma(np.add(k, 1))


def hyp2f2_1f1_series(a1: int, a2: int, b1: int, b2: int, x: Sequence[Real], scale=1.0):
    '''compute generalized hypergeometric function 2F2 from finite series of 1F1

    2F2(a1,a2;b1,b2;x) = \\sum_n (a1)_n(a2)_n/(b1)_n(b2)_n * x^n/n!

    2F2 is computed from a finite sum of Kummer's confluent hypergeometric function 1F1.
    This is only possible when b2>a2.

    2F2(a1,a2;b1,b2;x) = exp(x)\\sum^{b-d}_{n=0} (b-d,n)(a+n-1,n)/(c+n-1,n)/(d+n-1,n)
                         1F1(a1+n;b1+n;-x) x^n/n!
                       = \\sum^{b-d}_{n=0} (b-d,n)(a+n-1,n)/(c+n-1,n)/(d+n-1,n)
                         1F1(b1-a1;b1+n;x) x^n/n!

    Args:
        a1, a2, b1, b2 (int)
        x (1d-array)
        scale (float or 1d-array)
    '''
    from scipy import special
    upper = a2 - b2
    if upper < 0:
        raise ValueError("a2 is smaller than b2, {} < {}".format(a2, b2))
    if upper - np.rint(upper) != 0:
        raise ValueError("expect a2-b2 an integer, obtained {}".format(a2 - b2))
    upper = int(upper)
    n = np.array(list(range(int(upper) + 1)))
    numer = general_comb(upper, n) * general_comb(a1 + n - 1, n)
    denom = general_comb(b1 + n - 1, n) * general_comb(b2 + n - 1, n) * special.factorial(n)
    comb = numer / denom
    hyp1f1_xn = np.zeros((len(x), upper + 1), dtype="float64")
    if np.all(x < 0):
        for i in n:
            hyp1f1_xn[:, i] = special.hyp1f1(a1 + i, b1 + i, x) * np.power(x, i) * scale
    else:
        for i in n:
            hyp1f1_xn[:, i] = special.hyp1f1(b1 - a1, b1 + i, -x) * np.power(x, i) * np.exp(x) * scale
    return np.dot(hyp1f1_xn, comb)


class Smearing:
    """class with different smearing schemes implemented as static method
    """

    @staticmethod
    def gaussian(x, x0, sigma):
        """Gaussian smearing
        """
        return (np.exp(-np.subtract(x, x0)**2 / sigma**2 / 2.0) / sigma / np.sqrt(2.0 * PI))

    @staticmethod
    def lorentzian(x, x0, gamma):
        """Gaussian smearing
        """
        return gamma / (np.subtract(x, x0)**2 + gamma**2) / PI


def _linspace_1d(start: Number, end: Number, n: int,
                 startpoint: bool = True,
                 endpoint: bool = True) -> Tuple[Number]:
    npts_inbetween = n - int(startpoint) - int(endpoint)
    step = (end - start) / (npts_inbetween + 1)
    if not startpoint:
        start = start + step
    return list(np.linspace(start, end, n, endpoint=endpoint))


def linspace(
        start: Union[Number, Tuple[Number]],
        end: Union[Number, Tuple[Number]],
        n: int,
        startpoint: bool = True,
        endpoint: bool = True) -> Union[Tuple[Tuple[Number]], Tuple[Number]]:
    """get grid points which is linearly distributed between starting and ending point

    Args:
        start: number or list of number
        end: number or list of number
        n (int): the number of grids to return
        startpoint (bool): whether to include the start point
        endpoint (bool): whether to include the end point

    Returns:
        A list of numbers if start and end are number.
        A list of lists of numbers if start and end are lists of numbers.
    """
    if n < 2:
        raise ValueError("there must be more than 1 points")

    try:
        n_dim = len(start)
        if n_dim != len(end):
            raise ValueError("dimenstion of start")
        lists = list(_linspace_1d(start[i], end[i], n,
                                  startpoint=startpoint,
                                  endpoint=endpoint) for i in range(n_dim))
        return list(list(x) for x in zip(*lists))

    except TypeError:
        return _linspace_1d(start, end, n,
                                         startpoint=startpoint,
                                         endpoint=endpoint)
