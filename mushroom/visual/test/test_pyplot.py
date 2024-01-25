# -*- coding: utf-8 -*-
"""unittest of cube io"""
import unittest as ut
import tempfile

try:
    import matplotlib.pyplot as plt
    PLT_INSTALLED = True
    del plt
except ImportError:
    PLT_INSTALLED = False

from mushroom.visual.pyplot import rc_gracify


class test_pyplot(ut.TestCase):
    """test pyplot object"""

    def test_rc_gracify(self):
        if not PLT_INSTALLED:
            return
        rc_gracify()


if __name__ == "__main__":
    ut.main()

