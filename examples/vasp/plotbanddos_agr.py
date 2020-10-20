#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""example to draw band structure along with DOS"""
import pathlib
from mushroom._core.graceplot import Plot
from mushroom._core.cell import Cell
from mushroom._core.kpoints import KPath
from mushroom.vasp import read_doscar, read_eigen

p = Plot.band_dos()
dirname = pathlib.Path(__file__).parent

c = Cell.read("POSCAR")
# get dos from DOSCAR
path = dirname / "DOSCAR"
dos = read_doscar(path)
egrid, tdos = dos.get_dos(transpose=True)
p[1].plot(tdos, egrid, symbol="none")

# get band energies from EIGENVAL
path = dirname / "EIGENVAL"
bs, _, kpts = read_eigen(path)
kp = KPath(kpts, c.b)
print(kp.x.shape)
print(bs.eigen[0, :, :].transpose().shape)
p[0].plot(kp.x, bs.eigen[0, :, :].transpose(), color="k", symbol="none")
print(len(p[0]))

p[0].x.set_major(grid=True)
p[0].x.set_spec(kp.special_x)

p[0].tight_graph(xscale=1.0)
p[1].tight_graph()
p.export(file="data_new.agr")
