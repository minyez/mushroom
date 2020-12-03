#!/usr/bin/env bash
# shellcheck disable=SC2034

# vasp executable
vaspexe="/gpfs/share/home/1501210186/program/vasp.5.4.4/bin/vasp_std"
# default number of tasks. used for non-hpc tasks
defaultnp=4
prec=Accurate
# ENCUTs to test
encuts=(
        800
        1000
        1270
)
# ENCUT / ENCUTGW
encutgwratios=(
               0.5
)
# NBANDS / total nbands
nbandsratios=(
              0.6
              0.7
              0.8
              0.9
              1.0
)
# modules to load
modules=()
