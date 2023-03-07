# -*- coding: utf-8 -*-
"""ABINIT related facilities"""
import os
try:
    abi_pp_base = os.environ["ABI_PP_BASE"]
except KeyError:
    abi_pp_base = None
if abi_pp_base is None:
    try:
        from mushroom.__config__ import abi_pp_base
    except ImportError:
        abi_pp_base = None

# prefix (before stand): format of pps, (directory name, extension name)
known_abi_pps = {
    "nc-sr-04_pbe": "psp8",
    "nc-fr-04_pbe": "psp8",
    "nc-sr-04_pbesol": "psp8",
    "nc-sr-04_pw": "psp8",
    "nc-fr-04_pw": "psp8",
    }

if abi_pp_base is not None:
    for cond in ["standard", "stringent"]:
        for name, ext in known_abi_pps.itmes():
            d = "{}_{}_{}".format(name, cond, ext)

