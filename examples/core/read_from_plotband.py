#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Read data from agr file, and create a new agr plot by Plot object
"""
from mushroom.visual.graceplot import Plot, extract_data_from_agr

p = Plot()

# plotband.agr is a file produced by py_band.py
_, data_all, _ = extract_data_from_agr("plotband.agr")

for i, (x, y) in enumerate(data_all):
    p[0].plot(x, y, color="k", symbol="none")
locs = [0.0000000, 0.5302880, 1.0605760, 1.5908640, 2.7334759]
labels = ["X", "G", "M", "X", "R"]
p[0].x.set_spec(locs, labels)
p[0].x.set_major(grid="on", ls="dotted", color="grey", lw=3)
p.tight_graph(xscale=1.0)
p[0].axhline(0.0, lw=1, color="k", ls="dotted")
p.write("redraw.agr")

