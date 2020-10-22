#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""example to draw DOS"""
import pathlib
from mushroom.graceplot import Plot
from mushroom.vasp import read_doscar

p = Plot()
dirname = pathlib.Path(__file__).parent
path = dirname / "DOSCAR"

dos = read_doscar(path)
tdos = dos.get_dos()
p.plot(dos.egrid, tdos, symbol="none")

p.tight_graph()
p.write(file="data_new.agr")
