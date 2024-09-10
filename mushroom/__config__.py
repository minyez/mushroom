#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""extract configurations from rc files"""
import os
import sys
from importlib import machinery

from mushroom import __NAME__

# a global configuration file
fn = __NAME__ + "rc"
dotfn = "." + fn
config_files = [
    os.path.join(os.environ["HOME"], "." + __NAME__, fn),
    os.path.join(os.environ["HOME"], dotfn),
    dotfn,
]

module_name = __NAME__ + '.__config__'

found_config = False


# pylint: disable=no-value-for-parameter,W1505
for config_file in config_files:
    if os.path.isfile(config_file):
        found_config = True
        # TODO: replace load_module with exec_module
        # Reference: https://github.com/wntrblm/nox/blob/afb5111f67eb35c4cc4974ee3e875cdb20199018/nox/tasks.py#L36
        machinery.SourceFileLoader(module_name, config_file).load_module()

del (config_files, config_file, machinery, module_name, os, sys)

