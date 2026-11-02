# -*- coding: utf-8 -*-
"""element facilities"""
from typing import Union
from re import sub

# pylint: disable=line-too-long
element_symbols = (
    'X',  # pseudo atom
    'H', 'He',
    'Li', 'Be', 'B', 'C', 'N', 'O', 'F', 'Ne',
    'Na', 'Mg', 'Al', 'Si', 'P', 'S', 'Cl', 'Ar',
    'K', 'Ca',
    'Sc', 'Ti', 'V', 'Cr', 'Mn', 'Fe', 'Co', 'Ni', 'Cu', 'Zn',
    'Ga', 'Ge', 'As', 'Se', 'Br', 'Kr',
    'Rb', 'Sr',
    'Y', 'Zr', 'Nb', 'Mo', 'Tc', 'Ru', 'Rh', 'Pd', 'Ag', 'Cd',
    'In', 'Sn', 'Sb', 'Te', 'I', 'Xe',
    'Cs', 'Ba',
    'La',
    'Ce', 'Pr', 'Nd', 'Pm', 'Sm', 'Eu', 'Gd', 'Tb', 'Dy', 'Ho', 'Er', 'Tm', 'Yb', 'Lu',
    'Hf', 'Ta', 'W', 'Re', 'Os', 'Ir', 'Pt', 'Au', 'Hg',
    'Tl', 'Pb', 'Bi', 'Po', 'At', 'Rn',
    'Fr', 'Ra',
    'Ac',
    'Th', 'Pa', 'U', 'Np', 'Pu',
    'Am', 'Cm', 'Bk', 'Cf', 'Es', 'Fm', 'Md', 'No', 'Lr',
    'Rf', 'Db', 'Sg', 'Bh', 'Hs', 'Mt', 'Ds', 'Rg', 'Cn',
    'Nh', 'Fl', 'Mc', 'Lv', 'Ts', 'Og',
)

nuclear_charges = {s: i for i, s in enumerate(element_symbols)}


def get_atomic_number(e: Union[str, int], allow_int: bool = True):
    """get the atomic number of element

    Args:
        e (str or int): the symbol or atomic number of element
            Integer values must be valid table indices; booleans are rejected.
            Strings have spaces and digits removed and are capitalized before lookup.
        allow_int (bool): allow parsing e as int for validity check

    Returns:
        int, atomic number of the element
    """
    an = None
    if isinstance(e, int):
        if not allow_int or isinstance(e, bool):
            raise ValueError("symbol must be str, not int")
        if 0 <= e < len(element_symbols):
            an = e
    if isinstance(e, str):
        e = sub(r"[\d ]", "", e)
        an = nuclear_charges.get(e.capitalize(), None)
    if an is None:
        raise ValueError("invalid element {}".format(e))
    return an


# ====================================================
# Standard atomic weight, or relative atomic mass of the element
# Data from NIST database 144, last update January 2015
# https://physics.nist.gov/cgi-bin/Compositions/stand_alone.pl
# The data is double-checked with Wolfram Language ElementData (WLE)
# In case that an atomic-weight interval is met in NIST,
# the data in WLE is used instead and noted below.
# All data are accurate to 6 decimals, if available
# WLE data used: H, Li, B, C, N, O, Mg, Si, S, Cl, Br, Tl
# The data for > Pu are from https://periodictable.com/
atomic_weights = (
    0.0,
    1.008, 4.002602,
    6.94, 9.012183, 10.81, 12.011, 14.007, 15.999, 18.998403, 20.1797,
    22.989769, 24.305, 26.981539, 28.085, 30.973762, 32.06, 35.45, 39.948,
    39.0983, 40.078,
    44.955908, 47.867, 50.9415, 51.9961, 54.938044, 55.845, 58.933194, 58.6934, 63.546, 65.38,
    69.723, 72.6308, 74.921595, 78.971, 79.904, 83.798,
    85.4678, 87.62,
    88.90584, 91.224, 92.90637, 95.95, 98, 101.07, 102.90550, 106.42, 107.8682, 112.414,
    114.818, 118.710, 121.760, 127.60, 126.90447, 131.293,
    132.905452, 137.327,
    138.90547,
    140.116, 140.90766, 144.242, 145, 150.36, 151.964, 157.25, 158.92535, 162.500, 164.93033, 167.259, 168.93422, 173.054, 174.9668,
    178.49, 180.94788, 183.84, 186.207, 190.23, 192.217, 195.084, 196.966569, 200.592,
    204.38, 207.2, 208.98040, 209, 210, 222,
    223, 226,
    227,
    232.0377, 231.03588, 238.02891, 237, 244,  # End at Pu
    243, 247, 247, 251, 252, 257, 258, 259, 262,
    267, 270, 269, 270, 270, 278, 281, 281, 285,
    286, 289, 289, 293, 293, 294,  # End at Og
)


def get_atomic_weight(e: Union[str, int]):
    """get the atomic weight of the element

    Args:
        e (str or int): the symbol or atomic number of element
            Integer values must be valid table indices; booleans are rejected.
            Strings have spaces and digits removed and are capitalized before lookup.

    Returns:
        float: atomic weight in unified atomic mass units
    """
    an = get_atomic_number(e)
    return atomic_weights[an]


# alias of get_atomic_weight
get_atomic_mass = get_atomic_weight
# ====================================================


l_channels = ['s', 'p', 'd', 'f', 'g', 'h', 'i', 'j', 'k']
l_int = {v: i for i, v in enumerate(l_channels)}

