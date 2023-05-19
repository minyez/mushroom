#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""extract configurations from rc files"""
import os
import sys
from importlib import machinery

from mushroom import __NAME__

# a global configuration file
fn = "." + __NAME__ + "rc"
config_files = [
    os.path.join(os.environ["HOME"], fn),
    fn,
]

# pylint: disable=no-value-for-parameter,W1505
for config_file in config_files:
    if os.path.isfile(config_file):
        # may replace load_module later
        machinery.SourceFileLoader(__NAME__ + '.__config__', config_file).load_module()

del (config_files, config_file, machinery, os, sys)

