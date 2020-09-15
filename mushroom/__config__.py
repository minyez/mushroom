#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
from importlib import machinery

__NAME__ = "mushroom"
# a global configuration file
config_file = os.path.join(os.environ["HOME"], "." + __NAME__ + "rc")

if os.path.isfile(config_file):
    machinery.SourceFileLoader(__NAME__ + '.__config__', config_file).load_module()

del(machinery, os)
