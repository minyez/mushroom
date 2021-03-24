#!/usr/bin/env bash
# shellcheck disable=SC2034

# vasp executable
vaspexe="vasp_std"
# default number of tasks. used for non-hpc calculation
defaultnp=4

# precision and convergence criteria
prec="Accurate"
ediff="1.0E-6"

# ENCUTs to test
# NOTE!!! Only the first kmesh will be used for ENCUT test
encuts=(
        400
        500
)
# KPOINTS (Gamma-centered) 
# NOTE!!! kmesh test will only be performed for the first ENCUT value
kmeshes=(
  "2 2 2"
  "4 4 4"
)

# screening parameter
hfscreen=0
# exact exchange
aexx=
# switch on thomas-fermi screening, use for SX-PBE/LDA
lthomas=0
# set non-zero to use ALGO=damp for hybrid calculation
use_damp=0

modules=()
