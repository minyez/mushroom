#!/usr/bin/env bash
# shellcheck disable=SC2034

# w2k executable
initlapw="init_lapw -b"
runlapw="run_lapw"
x="x"
# modules to load
modules=()

# default number of tasks. used for non-hpc tasks
defaultnp=1
# planewave cutoff to use
rkmax=
# scf k points
kpts_scf=216
# energy convergence in eV
ecev=1E-06
# energy convergence in Ry
ec=

# ===============================
# For optical calculations
# k mesh for optic
kpts_opt=1728

# choices for optic
# 1 2 3 for Re xx, Re yy and Re zz
# this is sufficient for ortho and non-SOC calculations
# add 4 5 6 for non-ortho. SOC not supported yet
op_choices=(1 2 3)

# broadening and scissors shift for kram, in eV
kram_broad=0.1
kram_shift=0.0

# ===============================
# variables usually do not change
# core-valence separation in init_lapw, empty to use default -6.0 eV
ecut=
