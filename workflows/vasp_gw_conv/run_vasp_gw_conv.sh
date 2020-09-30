#!/usr/bin/env bash

# ===== variables =====
# vasp executable
vaspexe="/gpfs/share/home/1501210186/program/vasp.5.4.4/bin/vasp_std"
# number of tasks
defaultnp=4
np=${SLURM_NTASKS:=$defaultnp}
vaspcmd="mpirun -np $np $vaspexe"
# pre-requisites from platform
module load intel/2017.1
# =====================
source ./vasp.sh

# ===== functions =====
gw_calc() {
  # 1: step to start. 1 or 2 to skip scf and diag
  # TODO change main stream to make it compatible with 1/2
  run_gw_3steps "$vaspcmd"
  gap=$(get_eigen_ik 1 "EIGENVAL" "OUTCAR" | awk '{print($2-$1)}')
  etime=$(get_wall "OUTCAR")
  echo "$gap $etime"
  rm -f ./*.tmp ./WAVE*
}
# =====================

# ===== main =====
if [ ! -f results.txt ]; then
  echo "ENCUT  ENCUTGW  NBANDS    Eg   time" > results.txt
fi

for encut in 800 1000 1270; do
    encutgw=$(echo "$encut 2.0" | awk '{print($1/$2)}')
    nbandsmax=$(echo "$encut 750 1139" | awk '{printf("%d",($1/$2)**1.5 * $3)}')
    for ratio in 0.5 0.6 0.7 0.8 0.9; do
        nbands=$(echo "$nbandsmax $ratio 192" | awk '{printf("%d",($1*$2) - ($1*$2) % $3)}')
        workdir="encut_${encut}_encutgw_${encutgw}_nbands_${nbands}"
        if [ -d "$workdir" ]; then
            continue
        fi
        mkdir -p "$workdir"
        sed "s/_encut_/$encut/g" INCAR.scf  > "$workdir"/INCAR.scf
        sed "s/_encut_/$encut/g;s/_nbands_/$nbands/g" INCAR.diag  > "$workdir"/INCAR.diag
        sed "s/_encut_/ENCUT = $encut/g;s/_nbands_/$nbands/g;s/_encutgw_/$encutgw/g" INCAR.gw  > "$workdir"/INCAR.gw
        cd "$workdir" || exit 1
        ln -s ../POSCAR POSCAR
        ln -s ../POTCAR POTCAR
        cp ../KPOINTS.scf KPOINTS.scf
        cp ../KPOINTS.gw KPOINTS.gw
        values=$(gw_calc 0)
        echo "$encut $encutgw $nbands $values" >> results.txt
        cd ..
    done
done

