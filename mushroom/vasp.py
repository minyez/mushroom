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
    def __read_splitted_atom_data(dls, nspins):
        data = np.array([x[1:] for x in dls])
        nedos = len(dls)
        nprjs = len(data[0]) // nspins
        # reshape to (nspins, nedos, nprjs)
        # first convert to (nedos, nspins, nprjs), then switch the first two axis
        return data.reshape((nedos, nspins, nprjs), order='F').swapaxes(0, 1)

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
    _logger.info(">> ISPIN = %d", nspins)
    _logger.info(">> NEDOS = %d", nedos)

    egrid = np.array([x[0] for x in lines[6:6+nedos]])
    # total density of states
    tdos = [x[1:1+nspins] for x in lines[6:6+nedos]]
    tdos = np.array(tdos).transpose()
    pdos = None
    if len(lines) > nedos + 7:
        nprjs = (len(lines[nedos+7]) - 1) // nspins
        pdos = np.zeros((nspins, nedos, natms, nprjs))
        for ia in range(natms):
            start = (ia+1) * (nedos+1) + 6
            pdos[:, :, ia, :] = __read_splitted_atom_data(lines[start:start+nedos], nspins=nspins)

    return {"egrid": egrid,
            "tdos": tdos,
            "efermi": efermi,
            "unit": 'ev',
            "pdos": pdos,
            }

def read_doscar(path="DOSCAR", reset_fermi=True, ncl=False):
    """read DOSCAR file and returns a DensitofStates object
    
    Args:
        path (str) : path to DOSCAR file. default to "DOSCAR"
        reset_fermi (bool) : unset Fermi energy obtained from DOSCAR
            this is useful when one wants a dos with it VBM as energy zero
        ncl (bool) : DOS file from non-collinear calculation

    Returns:
        a DensityOfStates object
    """
    d = _dict_read_doscar(path=path, ncl=ncl)
    if reset_fermi:
        d["efermi"] = None
    return DensityOfStates(**d)

# pylint: disable=R0914
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
    # extra line "tot" for more than 1 atom
    has_tot_line = int(natms > 1)
    # remove the ion index and tot
    prjs = lines[7].split()[1:-1]
    nprjs = len(prjs)
    kpt_span = nbands*(natms+4+has_tot_line)+3
    if len(lines) > (1+nkpts*kpt_span):
        nspins = 2
    eigen = np.zeros((nspins, nkpts, nbands))
    occ = np.zeros((nspins, nkpts, nbands))
    weight = np.zeros(nkpts)
    pwav = np.zeros((nspins, nkpts, nbands, natms, nprjs))
    for ispin in range(nspins):
        for ikpt in range(nkpts):
            weight[ikpt] = float(lines[ikpt*kpt_span+2].split()[-1])
            for ib in range(nbands):
                # the line index with prefix band
                start = ispin * (1+nkpts*kpt_span) + \
                        1 + ikpt * kpt_span + ib*(natms+4+has_tot_line) + 3
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

