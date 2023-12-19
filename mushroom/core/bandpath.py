#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""utilities for k-point path for band structure calculation"""
from mushroom.core.typehint import Latt3T3
from mushroom.core.crystutils import get_recp_latt


class BandPathAFLOW:
    """class to handle k-point paths for band structure

    Args:
        latt (ndarray)
    """

    def __init__(self, latt: Latt3T3, space_group: int):
        self.latt = latt
        self.space_group = space_group


if __name__ == '__main__':
    pass
