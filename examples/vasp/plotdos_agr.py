#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""example to draw DOS"""
import pathlib
from mushroom._core.graceplot import Plot
from mushroom.vasp import read_doscar

p = Plot()
dirname = pathlib.Path(__file__).parent
path = dirname / "DOSCAR"

dos = read_doscar(path)
egrid, tdos = dos._get_dos(transpose=True)
p.plot(egrid, tdos, symbol="none")

p.tight_graph()
p.export(file="data_new.agr")
