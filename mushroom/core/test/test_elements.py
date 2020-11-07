#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import unittest as ut
from collections import OrderedDict

from mushroom.core.elements import atomic_weights, element_symbols


class test_elem_symbols(ut.TestCase):

    def test_consistency(self):
        self.assertEqual(len(atomic_weights), len(element_symbols))
        # check duplicates in element symbols
        od = OrderedDict.fromkeys(element_symbols)
        self.assertEqual(len(element_symbols), len(od.keys()))

    def test_right_order(self):
        oi = -1
        for e in ['H', 'C', 'Na', 'S', 'Ga', 'As', 'Pd', 'La']:
            self.assertIn(e, element_symbols)
            ni = element_symbols.index(e)
            self.assertTrue(ni > oi)
            oi = ni


if __name__ == '__main__':
    ut.main()
