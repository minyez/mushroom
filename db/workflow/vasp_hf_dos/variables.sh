#!/usr/bin/env bash
# shellcheck disable=SC2034

# vasp executable
vaspexe="vasp_std"
# default number of tasks. used for non-hpc tasks
defaultnp=1
# convergence
ediff=1E-06
# planewave cutoff to use
encut=400
# smearing
# precision
prec="Accurate"
hfscreen=0
lthomas=0
# set non-zero to use ALGO=damp for hybrid calculation
use_damp=0
# modules to load
modules=()

# TODO multiplier for DOS kmesh. not work yet
kmult_dos=2

