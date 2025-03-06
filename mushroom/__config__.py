# -*- coding: utf-8 -*-
"""Extract configurations from rc files"""
import os
import sys
import importlib.util
from importlib.machinery import SourceFileLoader

from mushroom import __NAME__

# A global configuration file
fn = __NAME__ + "rc"
dotfn = "." + fn
config_files = [
    os.path.join(os.environ["HOME"], "." + __NAME__, fn),
    os.path.join(os.environ["HOME"], dotfn),
    dotfn,
]

module_name = __NAME__ + ".__config__"
found_config = False

for config_file in config_files:
    if os.path.isfile(config_file):
        found_config = True
        loader = SourceFileLoader(module_name, config_file)
        spec = importlib.util.spec_from_loader(module_name, loader)
        if spec is not None:
            module = importlib.util.module_from_spec(spec)
            loader.exec_module(module)
            sys.modules[module_name] = module  # Ensure it's accessible globally

# Cleanup namespace
del (config_files, config_file, importlib, module_name, os, sys, SourceFileLoader)
