# -*- coding: utf-8 -*-
"""utilities of vasp"""
from os.path import realpath
from io import StringIO
import numpy as np

from mushroom._core.logger import create_logger
from mushroom._core.dos import DensityOfStates
from mushroom._core.bs import BandStructure

_logger = create_logger("vasp")
del create_logger

def _dict_read_doscar(path="DOSCAR", ncl=False):
    """read DOSCAR file and returns a dict
    
    Args:
        path (str) : path to DOSCAR file. default to "DOSCAR"
        ncl (bool) : DOS file from non-collinear calculation

    Returns:
        dict

    TODO:
        - automatic ncl check
    """
    _logger.info("Reading DOSCAR from %s", realpath(path))
    with open(path, 'r') as h:
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
    pdos = None
    #for ia in range(natms):
    #    pdos_atom = []
    #    for line in lines[6+(ia+1)*(nedos+1):6+(ia+2)*(nedos+1)-1]:
    #        pdos_atom.append(line[1:])
    #    pdos.append(pdos_atom)
    #pdos = np.array(pdos)
    return {"egrid": egrid,
            "tdos": tdos,
            "efermi": efermi,
            "unit": 'ev',
            "pdos": pdos,
            }

def read_doscar(path="DOSCAR", ncl=False):
    """read DOSCAR file and returns a DensitofStates object
    
    Args:
        path (str) : path to DOSCAR file. default to "DOSCAR"
        ncl (bool) : DOS file from non-collinear calculation

    Returns:
        a DensityOfStates object
    """
    return DensityOfStates(**_dict_read_doscar(path=path, ncl=ncl))


def _dict_read_procar(path="PROCAR"):
    """read PROCAR file

    Args:
        path (str) : path to PROCAR file. default to "PROCAR"
    """
    def __read_band_data(dls):
        """Read data from datalines in the form

        band n # energy x.xxxx # occ. x.xxxxxx

        ion s py pz ....
        1 0.0 0.0 0.0 ...
        2 0.0 0.0 0.0 ...
        """
        eo = dls[0].split()
        e, o = map(float, (eo[-4], eo[-1]))
        s = [" ".join(x.split()[1:-1]) for x in dls[3:]]
        return e, o, np.loadtxt(StringIO("\n".join(s)))

    with open(path, 'r') as h:
        lines = h.readlines()[1:]
    l = lines[0].split()
    nkpts, nbands, natms = map(int, [l[3], l[7], l[-1]])
    nspins = 1
    # remove the ion index and tot
    prjs = lines[7].split()[1:-1]
    nprjs = len(prjs)
    if len(lines) > (1+nkpts*(nbands*(natms+4)+3)):
        nspins = 2
    eigen = np.zeros((nspins, nkpts, nbands))
    occ = np.zeros((nspins, nkpts, nbands))
    weight = np.zeros(nkpts)
    pwav = np.zeros((nspins, nkpts, nbands, natms, nprjs))
    for ispin in range(nspins):
        for ikpt in range(nkpts):
            weight[ikpt] = float(lines[ikpt*(nbands*(natms+4)+3)+2].split(-1))
            for ib in range(nbands):
                # the line index with prefix band
                start = ispin * (1+nkpts*(nbands*(natms+4)+3)) + \
                        1 + ikpt * (nbands*(natms+4)+3) + ib*(natms+4) + 3
                eigen[ispin, ikpt, ib], occ[ispin, ikpt, ib], pwav[ispin, ikpt, ib, :, :] \
                        = __read_band_data(lines[start:start+natms+3])
    return {"eigen": eigen,
            "occ": occ,
            "weight": weight,
            "unit": 'ev',
            "pwav": pwav,
            "prjs": prjs,
            }

def read_procar(path="PROCAR"):
    """read PROCAR and return a BandStructure object

    Args:
        path (str) : path to the PROCAR file
    """
    return BandStructure(**_dict_read_procar(path=path))

