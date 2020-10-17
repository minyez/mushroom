#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Read data from agr file, and create a new agr plot by Plot object
"""
from mushroom._core.graceplot import Plot, extract_data_from_agr

p = Plot()

# plotband.agr is a file produced by py_band.py
data_all = extract_data_from_agr("plotband.agr")

for i, (x, y) in enumerate(data_all):
    p[0].plot(x, y, color="k", symbol="none")

p.tight_graph(xscale=1.0)
p.export("redraw.agr")
