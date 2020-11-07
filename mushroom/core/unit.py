# -*- coding: utf-8 -*-
"""Objects to manipulate units of physical quantities"""
from mushroom.core.constants import ANG2AU, EV2HA, EV2RY, RY2HA

class UnitError(Exception):
    """exception for unit manipulation"""

class EnergyUnit:
    """Base class for controlling energy unit

    Args:
        eunit (str)
    """

    _defaul_eu = 'ev'
    _valid_eu = ['ev', 'ry', 'au']
    _conv_eu = {
        ('ev', 'ry'): EV2RY,
        ('ev', 'au'): EV2HA,
        ('ry', 'au'): RY2HA,
    }

    def __init__(self, eunit: str = None):
        if eunit is None:
            self._eunit = self._defaul_eu
        else:
            self._check_valid_eunit(eunit)
        self._eunit = eunit.lower()

    def _get_eunit_conversion(self, unit_to: str) -> float:
        self._check_valid_eunit(unit_to)
        tu = unit_to.lower()
        fu = self._eunit
        pair = (fu, tu)
        co = 1.
        if pair in self._conv_eu:
            co = self._conv_eu[pair]
        elif pair[::-1] in self._conv_eu:
            co = 1.0 / self._conv_eu[pair[::-1]]
        return co

    def _check_valid_eunit(self, eunit: str):
        u = eunit.lower()
        if u not in self._valid_eu:
            info = "{} is not a valid energy unit".format(eunit)
            raise UnitError(info)



class LengthUnit:
    """Base class for controlling length unit

    Args:
        lunit (str)
    """

    _default_lu = 'ang'
    _valid_lu = ['ang', 'au', 'bohr',]
    _conv_lu = {
        ('ang', 'au'): ANG2AU,
        ('ang', 'bohr'): ANG2AU,
    }

    def __init__(self, lunit: str = None):
        if lunit is None:
            self._lunit = self._default_lu
        else:
            self._check_valid_lunit(lunit)
        self._lunit = lunit.lower()

    def _get_lunit_conversion(self, unit_to: str) -> float:
        self._check_valid_lunit(unit_to)
        tu = unit_to.lower()
        fu = self._lunit
        pair = (fu, tu)
        co = 1
        if pair in self._conv_lu:
            co = self._conv_lu[pair]
        elif pair[::-1] in self._conv_lu:
            co = 1.0 / self._conv_lu[pair[::-1]]
        return co

    def _check_valid_lunit(self, lunit: str):
        u = lunit.lower()
        if u not in self._valid_lu:
            info = "{} is not a valid length unit".format(lunit)
            raise UnitError(info)

