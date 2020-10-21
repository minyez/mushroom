#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""A simple example for creating xmgrace subplots in mushroom"""
import numpy as np
from mushroom._core.graceplot import Plot

x = np.linspace(-1, 1)
y = np.sin(x)
p = Plot(1, 2, hgap=0., width_ratios="2:3")
p.set_default(font=2)
p.plot(x, y, label="sin(x)", color="red", symbol="none")
p[1].plot(x, 2.0 * y)
p[0].set_xlim(-1, 1)
p[0].set_ylim(-1, 1)
p[1].set_ylim(-2, 2)
p.tight_graph()
p[0].set_legend(loc='upper center')
p[1].set_yticklabel(switch="off")
p.title("grace test")
p.write(file="sin.agr")
