#!/usr/bin/env bash
# shellcheck disable=SC2034

# vasp executable
vaspexe="vasp_std"
#vaspexe="/gpfs/share/home/1501210186/program/vasp.5.4.4/bin/vasp_std"
# default number of tasks. used for non-hpc tasks
defaultnp=4
# planewave cutoff to use
encut=500
# precision
prec="Accurate"
# screening
hfscreen=0
# modules to load
modules=()