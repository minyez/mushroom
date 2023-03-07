#!/usr/bin/env bash
# shellcheck disable=SC2034

# gap version
gapver="2e"
gapdir=""
# gapinit and gapexe directly specify the executable and overwrite gapver and gapdir
gapinit=""
gapexe=""
# casename of calculation
casename="case"
# default number of tasks. used for non-hpc tasks
defaultnp=4
# number of LOs to add
nlos=(
  0
  1
  2
)
# delta l
dl=(
  0
  1
  2
)
# number of GW kpoints
nkp=8
# modules to load
modules=()
