#!/usr/bin/env bash
# shellcheck disable=SC2034

# vasp executable
vaspexe="/gpfs/share/home/1501210186/program/vasp.5.4.4/bin/vasp_std"
# default number of tasks. used for non-hpc tasks
defaultnp=4
# planewave cutoff to use
encut=500
# qmesh reduction
nkredx=1
nkredy=1
nkredz=1
# screening. 0 for PBE0, 0.2 for HSE06 and 0.3 for HSE03
hfscreen=0
# modules to load
modules=()
