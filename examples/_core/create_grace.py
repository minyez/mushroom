#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""A simple example for core facilities"""
import numpy as np
from mushroom._core.graceplot import Plot

x = np.linspace(-1, 1)
y = np.sin(x)
p = Plot()
p.add(x, y)
p.set_xlimit(-1, 1)
p.set_ylimit(-1, 1)
p.export(file="sin.agr")
