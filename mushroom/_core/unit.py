# -*- coding: utf-8 -*-
"""Objects to manipulate units of physical quantities"""
from mushroom._core.constants import ANG2AU, EV2HA, EV2RY, RY2HA


class UnitError(Exception):
    """exception for unit manipulation"""


class EnergyUnit:
    '''Base class for controlling energy unit

    Args:
        eunit (str)
    '''

    _defaul_eu = 'ev'
    _valid_eu = ['ev', 'ry', 'au']
    _conv_eu = {
        ('ev', 'ry'): EV2RY,
        ('ev', 'au'): EV2HA,
        ('ry', 'au'): RY2HA,
    }

    def __init__(self, eunit=None):
        if eunit is None:
            self._eunit = self._defaul_eu
        else:
            self._check_valid_eunit(eunit)
        self._eunit = eunit.lower()

    def _get_eunit_conversion(self, unit_to):
        self._check_valid_eunit(unit_to)
        tu = unit_to.lower()
        fu = self._eunit
        pair = (fu, tu)
        co = 1
        if pair in self._conv_eu:
            co = self._conv_eu[pair]
        elif pair[::-1] in self._conv_eu:
            co = 1.0 / self._conv_eu[pair[::-1]]
        return co
    
    def _check_valid_eunit(self, eunit):
        try:
            assert isinstance(eunit, str)
            u = eunit.lower()
            assert u in self._valid_eu
        except AssertionError:
            raise UnitError("allowed energy unit {}, {} parsed".format(
                self._valid_eu, eunit))


class LengthUnit:
    '''Base class for controlling length unit

    Args:
        lunit (str)
    '''

    _default_lu = 'ang'
    _valid_lu = ['ang', 'au']
    _conv_lu = {
        ('ang', 'au'): ANG2AU,
    }

    def __init__(self, lunit=None):
        if lunit is None:
            self._lunit = self._default_lu
        else:
            self._check_valid_lunit(lunit)
        self._lunit = lunit.lower()

    def _get_lunit_conversion(self, unit_to):
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

    def _check_valid_lunit(self, lunit):
        try:
            assert isinstance(lunit, str)
            u = lunit.lower()
            assert u in self._valid_lu
        except AssertionError:
            info = "allowed length unit {}, {} parsed".format(
                self._valid_lu, lunit)
            raise UnitError(info)
