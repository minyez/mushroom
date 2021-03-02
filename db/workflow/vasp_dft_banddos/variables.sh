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
sigma=0.05
ispin=1
# precision
prec="Accurate"
# modules to load
modules=()
# for band-decomposed charge density after SCF calculation
# always decomposed to band and kpoint
iband=""
kpuse=""
# TODO multiplier for DOS kmesh. not work yet
kmult_dos=2

# LDA+U setting
# only LDAUTYPE=2 is used, hence ispin=2 is imposed and only U-J matters.
# note that LASPH will be also switched on
ldaul=""
ldauu=""
