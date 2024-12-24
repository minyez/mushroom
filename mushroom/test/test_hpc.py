#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test hpc facilities"""
import unittest as ut
import tempfile
import pathlib
from io import StringIO

from mushroom.hpc import (current_platform, current_use_pbs,
                          get_scheduler_header, add_scheduler_header)
from mushroom.hpc import SbatchOptions, SbatchScript, is_slurm_enabled


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


class test_slurm_environment(ut.TestCase):

    def test_is_slurm_enabled(self):
        is_slurm_enabled()


class test_sbatch_options(ut.TestCase):

    template_string = """#SBATCH -J jobname
#SBATCH --nodes 2
#SBATCH --exclusive
#SBATCH --ntasks-per-node 36
#SBATCH --cpus-per-task 2
#SBATCH --mail-type fail
#SBATCH -x cpu01,cpu10"""
    template = StringIO(template_string)

    def test_export_script(self):
        sbatch_options = SbatchOptions(self.template)
        slist_raw = sorted(self.template_string.split("\n"))
        # should recover the raw template
        slist = sorted(sbatch_options.export_script())
        self.assertListEqual(slist, slist_raw)
        sbatch_options.set(unknown_option=10)
        # an unknown option should not be parsed
        slist = sorted(sbatch_options.export_script())
        self.assertListEqual(slist, slist_raw)


class test_sbatch_script(ut.TestCase):

    template_string = """#SBATCH -J jobname
#SBATCH --nodes 2
#SBATCH --exclusive
#SBATCH --ntasks-per-node 36
#SBATCH --cpus-per-task 2
#SBATCH -x cpu01,cpu10

srun aims.x
"""
    template = StringIO(template_string)

    def test_init_from_template(self):
        sbatch_script = SbatchScript(template=self.template)
        print(sbatch_script)
        self.assertEqual(sbatch_script.commands.strip(), "srun aims.x")

    def test_write(self):
        sheban = "#!/bin/bash"
        commands = "srun vasp_std > vasp.out"
        sbatch_script = SbatchScript(sheban=sheban, commands=commands)
        # no sbatch options
        self.assertEqual(str(sbatch_script), "\n".join([sheban, commands]))
        tf = tempfile.NamedTemporaryFile()
        sbatch_script.write(tf.name)
        tf.close()


if __name__ == "__main__":
    ut.main()

