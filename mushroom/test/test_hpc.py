#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test hpc facilities"""
import unittest as ut
import tempfile
# import pathlib

from mushroom.hpc import (current_platform, current_use_pbs,
                          get_scheduler_header, add_scheduler_header)


class test_platform(ut.TestCase):
    """test the platform recogniztion on the HPC"""

    def test_no_platform_registered(self):
        """generally the CI platform and localhost is not registered"""
        self.assertIsNone(current_platform)
        self.assertFalse(current_use_pbs)
        self.assertRaises(ValueError, get_scheduler_header,
                          current_platform, use_pbs=current_use_pbs)
        tf = tempfile.NamedTemporaryFile(suffix=".sh")
        with open(tf.name, 'w') as h:
            print("#!/bin/bash\necho 'Hello World!'", file=h)
        add_scheduler_header(tf.name, platform=None)
        tf.close()

# # only works when dynamically loading rc file is possible
#     def test_fake_platform(self):
#         """fake platform from rc file"""
#         temprc = '~/.mushroomrc'
#         temprc = pathlib.Path(temprc).expanduser()
#         if temprc.exists():
#             return
#         s = """sbatch_headers = {
#     "fake": ["-J test",
#              "-o stdout",],}
# pbs_headers = {
#     "fake": ["-J test",
#              "-o stdout",],}
# """
#         with temprc.open('w') as h:
#             print(s, file=h)
#         header = get_scheduler_header("fake", use_pbs=False)
#         self.assertEqual(header, "#SBATCH -J test\n#SBATCH -o stdout\n")
#         header = get_scheduler_header("fake", use_pbs=True)
#         self.assertEqual(header, "#PBS -J test\n#PBS -o stdout\n")
#         tf = tempfile.NamedTemporaryFile(suffix=".sh")
#         with open(tf.name, 'w') as h:
#             print("#!/bin/bash\necho 'Hello World!'", file=h)
#         add_scheduler_header(tf.name, platform="fake")
#         tf.close()
#         temprc.unlink()


if __name__ == "__main__":
    ut.main()

