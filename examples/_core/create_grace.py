#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""A simple example for creating xmgrace plots in mushroom"""
import numpy as np
from mushroom._core.graceplot import Plot

x = np.linspace(-1, 1)
y = np.sin(x)
p = Plot(2, 2)
p.add(x, y)
p.set_xlimit(-1, 1)
p.set_ylimit(-1, 1)
p.set_xlabel("x")
p.set_ylabel("sin(x)")
p.set_title("grace test")
p.export(file="sin.agr")
