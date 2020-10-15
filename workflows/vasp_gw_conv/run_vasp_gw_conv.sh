#!/usr/bin/env bash

# load pre-requisites from platform
# =====================
source ./variables.sh
source ./common.sh
source ./vasp.sh

np=${SLURM_NTASKS:=$defaultnp}
vaspcmd="mpirun -np $np $vaspexe"
module load "${modules[@]}"
# ===== functions =====
function gw_calc () {
  run_gw_3steps "$vaspcmd"
  gap=$(eigen_outcar_vbcb_ik "EIGENVAL" "OUTCAR" 1 | awk '{print($2-$1)}')
  etime=$(wall_time "OUTCAR")
  echo "$gap $etime"
  rm -f ./*.tmp ./WAVE*
}
# =====================

# ===== run_vasp_gw_conv =====
function run_vasp_gw_conv () {
  if [ ! -f results.txt ]; then
    echo "ENCUT  ENCUTGW  NBANDS    Eg   time" > results.txt
  fi
  comment_datetime >> results.txt
  
  for encut in "${encuts[@]}"; do
    nbandsmax=$(echo "$encut 750 1139" | awk '{printf("%d",($1/$2)**1.5 * $3)}')
    for encutgwratio in "${encutgwratios[@]}"; do
      encutgw=$(echo "$encut $encutgwratio" | awk '{print($1*$2)}')
      for nbandsratio in "${nbandsratios[@]}"; do
        nbands=$(echo "$nbandsmax $nbandsratio $np" | awk '{printf("%d",($1*$2) - ($1*$2) % $3)}')
        workdir="encut_${encut}_encutgw_${encutgw}_nbands_${nbands}"
        if [ -d "$workdir" ]; then
          continue
        fi
        mkdir -p "$workdir"
        sed "s/_encut_/$encut/g" INCAR.scf  > "$workdir"/INCAR.scf
        sed "s/_encut_/$encut/g;s/_nbands_/$nbands/g" INCAR.diag  > "$workdir"/INCAR.diag
        sed "s/_encut_/$encut/g;s/_nbands_/$nbands/g;s/_encutgw_/$encutgw/g" INCAR.gw  > "$workdir"/INCAR.gw
        cd "$workdir" || exit 1
        ln -s ../POSCAR POSCAR
        ln -s ../POTCAR POTCAR
        cp ../KPOINTS.scf KPOINTS.scf
        cp ../KPOINTS.gw KPOINTS.gw
        values=$(gw_calc 0)
        cd ..
        echo "$encut $encutgw $nbands $values" >> results.txt
      done
    done
  done
}

run_vasp_gw_conv "$@"

