#!/usr/bin/env bash

source ./variables.sh
source ./common.sh
source ./vasp.sh

np=${SLURM_NTASKS:=$defaultnp}

vaspcmd="mpirun -np $np $vaspexe"
# load pre-requisite modules
module load "${modules[@]}"

reqs=(INCAR.pbe INCAR.coarse INCAR.hf KPOINTS.scf POTCAR POSCAR)
raise_missing_prereq "${reqs[@]}"

# create necessary files
workdir=hf_scf
raise_isdir "$workdir"
mkdir "$workdir"
# process INCAR tags from variables
sed "s/_encut_/$encut/g" INCAR.pbe > "$workdir/INCAR.pbe"
sed "s/_encut_/$encut/g;s/_hfscreen_/$hfscreen/g" INCAR.coarse > "$workdir/INCAR.coarse"
sed -i "s/_nkredx_/$nkredx/g;s/_nkredy_/$nkredy/g;s/_nkredz_/$nkredz/g" "$workdir/INCAR.coarse"
sed "s/_encut_/$encut/g;s/_hfscreen_/$hfscreen/g" INCAR.hf > "$workdir/INCAR.hf"
cp KPOINTS.scf "$workdir/"

cd "$workdir" || exit 1
ln -s ../POSCAR POSCAR
ln -s ../POTCAR POTCAR
# start calculation
run_hf_3steps "$vaspcmd"
# TODO add data extraction
