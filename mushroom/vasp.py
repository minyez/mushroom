# -*- coding: utf-8 -*-
"""utilities of vasp"""
from os.path import realpath
import numpy as np

from mushroom._core.logger import create_logger
from mushroom._core.dos import DensityOfStates

_logger = create_logger("vasp")
del create_logger

def read_doscar(dosfile="DOSCAR", ncl=False):
    """read DOSCAR file
    
    Args:
        dosfile (str) : path to DOSCAR file
        ncl (bool) : DOS file from non-collinear calculation

    Returns:
        a DensityOfStates object

    TODO:
        - automatic ncl check
    """
    _logger.info("Reading DOSCAR from %s", realpath(dosfile))
    with open(dosfile, 'r') as h:
        lines = [l.split() for l in h.readlines()]
    natms = int(lines[0][0])
    nedos, efermi = map(float, lines[5][2:4])
    nedos = int(nedos)
    if len(lines[6]) == 3:
        nspins = 1
    else:
        nspins = 2
    if ncl:
        raise NotImplementedError
    _logger.info("ISPIN = %d", nspins)
    _logger.info("NEDOS = %d", nedos)

    egrid = np.array([x[0] for x in lines[6:6+nedos]])

    # total density of states
    tdos = [x[1:1+nspins] for x in lines[6:6+nedos]]
    tdos = np.array(tdos).transpose()
    # TODO read pdos
    #pdos = []
    #for ia in range(natms):
    #    pdos_atom = []
    #    for line in lines[6+(ia+1)*(nedos+1):6+(ia+2)*(nedos+1)-1]:
    #        pdos_atom.append(line[1:])
    #    pdos.append(pdos_atom)
    #pdos = np.array(pdos)
    return DensityOfStates(egrid, tdos, efermi=efermi, unit='ev')

