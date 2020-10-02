#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""A simple example for creating xmgrace subplots in mushroom"""
import numpy as np
from mushroom._core.graceplot import Plot

x = np.linspace(-1, 1)
y = np.sin(x)
p = Plot(1, 2)
p.add(x, y, label="sin(x)")
p[1].add(x, 2.0 * y)
p.set_xlimit(-1, 1)
p.set_ylimit(-1, 1)
p[1].set_ylimit(-2, 2)
p.set_title("grace test")
p.export(file="sin.agr")
