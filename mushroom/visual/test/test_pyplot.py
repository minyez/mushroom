# -*- coding: utf-8 -*-
"""unittest of cube io"""
import unittest as ut
import tempfile

from mushroom.visual.pyplot import *


class test_pyplot(ut.TestCase):
    """test pyplot object"""

    def test_rc_gracify(self):
        rc_gracify()


if __name__ == "__main__":
    ut.main()

