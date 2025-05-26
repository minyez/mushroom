# -*- coding: utf-8 -*-
"""facilities for equation of state (EOS)

Implemented:
    Murnaghan EOS (m)
    Birch-Murnaghan EOS (bm)

Rules of parameters:
    Usually three parameters are required: E0, V0, B0, i.e.
    equilirium energy, equilirium volume and bulk modulus.
    For some EOS, there is an extra B', derivative of modulue wrt pressure.

    In terms of the order of parameters, E0, V0, B0 always appear the first
    in order, then follows: B' (bp).
"""
import numpy as np
from typing import List
try:
    from scipy.optimize import curve_fit
except ImportError:
    curve_fit = None
from mushroom.core.ioutils import raise_no_module


def _Murnaghan(v: np.ndarray, e0: float, v0: float,
               b0: float, bp: float) -> np.ndarray:
    """Murnaghan EOS

    E(V) = E0 + B0 * V0 *
           [x^(1-B')/B'/(B'-1) + x/B' - 1/(B'-1)]

    where x=V/V0
    """
    x = v / v0
    return e0 + b0 * v0 * (np.power(x, 1 - bp) / bp / (bp - 1) + x / bp - 1 / (bp - 1))


def _BirchMurnaghan(v: np.ndarray, e0: float, v0: float,
                    b0: float, bp: float) -> np.ndarray:
    """Birch-Murnaghan EOS

    E(V) = E0 + 9/16 * V0 * B0 *
           {[x^(-2/3)-1]^3*B' + [x^(-2/3)-1]^2*[6 - 4*x^(-2/3)]}

    where x=V/V0
    """
    x = v / v0
    xm23 = np.power(x, -2.0 / 3.0)
    return e0 + 9.0 / 16.0 * v0 * b0 * ((xm23 - 1.0) ** 3 * bp + (xm23 - 1.0) ** 2 * (6.0 - 4.0 * xm23))


# key: name of EOS
# value: 3-member tuple: (function object, short-name, number of parameters)
_dict_eos = {
    "bm": (_BirchMurnaghan, "Birch-Murnaghan", 4),
    "m": (_Murnaghan, "Murnaghan", 4),
}

available_eos = tuple(_dict_eos.keys())


def get_eos(name: str):
    """get the EOS function by the name"""
    func, shortname, nparams = _dict_eos.get(name.lower(), (None, None, None))
    if func is None:
        raise KeyError("Unknown name for EOS: {}".format(name))
    return func, shortname, nparams


def fit_eos(name, vols, enes,
            initial_guess: List[float] = None,
            vfit: List[float] = None):
    """Fit equation-of-state with input volume and energies

    Args:
        name (str)
        vols, enes (1-d array)
        initial_guess (tuple/list)
        vfit (1-d array)

    Returns:
        tuple (popt), float (r2), 1-d array (e) if vfit is None, otherwise
        tuple (popt), float (r2), 1-d array (e), 1-d array (vfit)

    """
    raise_no_module(curve_fit, "scipy.optimize.curve_fit")

    opts_curve_fit = {"maxfev": 5000}
    eosfunc, _, nparams = get_eos(name)

    vols = np.array(vols)
    enes = np.array(enes)

    if initial_guess is not None:
        if len(initial_guess) != nparams:
            raise ValueError("invalid initial guess input")
    else:
        e0 = min(enes)
        v0 = vols[np.where(enes == e0)][0]
        b0 = 1.0
        bp = 4.0
        if nparams == 4:
            initial_guess = [e0, v0, b0, bp]
        else:
            raise NotImplementedError

    popt, pcov = curve_fit(eosfunc, vols, enes, p0=initial_guess,
                           **opts_curve_fit)
    # perr = np.sqrt(np.diag(pcov))
    r2 = 1 - np.sum((enes - eosfunc(vols, *popt))**2) / np.sum(
        (enes - np.mean(enes))**2)

    e = eosfunc(vols, *popt)
    if vfit is not None:
        efit = eosfunc(vfit, *popt)
        return popt, r2, e, efit
    return popt, r2, e
