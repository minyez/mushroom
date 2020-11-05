#!/usr/bin/env bash
# shellcheck disable=SC2034

# vasp executable
vaspexe="vasp_std"
# default number of tasks. used for non-hpc tasks
defaultnp=1
# planewave cutoff to use
encut=400
ediff=1E-06
prec="Accurate"
# qmesh reduction
nkredx=1
nkredy=1
nkredz=1
# screening. 0 for PBE0, 0.2 for HSE06 and 0.3 for HSE03
hfscreen=0
use_damp=0
lthomas=0
# modules to load
modules=()
