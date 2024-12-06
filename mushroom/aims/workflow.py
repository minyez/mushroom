# -*- coding: utf-8 -*-
"""workflow objects for FHI-aims"""
import pathlib

from mushroom.aims.stdout import StdOut


class AimsWorkdir:
    """Class to handle a FHI-aims calculation working folder"""

    def __init__(self, dirpath: str, aimsout: str = "aims.out", aimserr: str = None):
        dirpath = pathlib.Path(dirpath).absolute()
        self.dirpath = dirpath
        self.path_control = dirpath / "control.in"
        self.path_geometry = dirpath / "geometry.in"
        self.path_aimsout = dirpath / aimsout
        self.path_aimserr = None
        if aimserr is not None:
            self.path_aimserr = dirpath / aimserr

        self.band_output_glob = "band[0-9][0-9][0-9][0-9].out"

        self.efermi = None
        self.nspin = None
        self.nelect = None

        # Objects to handle inputs and outputs
        self._control = None
        self._geometry = None
        self._aimsout = None

    def load_output(self):
        self._aimsout = StdOut(self.path_aimsout, lazy_load=False)

    def is_finished(self):
        return self._aimsout.is_finished(False)

    def is_converged(self):
        return self._aimsout.is_finished(True)
