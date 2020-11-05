#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test hpc facilities"""
import unittest as ut

from mushroom.core.hpc import current_platform, current_use_pbs, get_scheduler_head

class test_platform(ut.TestCase):
    """test the platform recogniztion on the HPC"""
    def test_no_platform_registered(self):
        """generally the CI platform and localhost is not registered"""
        self.assertIsNone(current_platform)
        self.assertFalse(current_use_pbs)
        self.assertRaises(ValueError, get_scheduler_head,
                          current_platform, use_pbs=current_use_pbs)

if __name__ == "__main__":
    ut.main()
