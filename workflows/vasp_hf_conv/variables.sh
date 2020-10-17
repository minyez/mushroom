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
  "4 4 4"
)

hfscreen=0
# switch on thomas-fermi screening, use for SX-PBE/LDA
lthomas=0

modules=()
