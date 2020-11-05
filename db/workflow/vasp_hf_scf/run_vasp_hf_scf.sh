#!/usr/bin/env bash

source ./variables.sh
source ./common.sh
source ./vasp.sh

np=${SLURM_NTASKS:=$defaultnp}
vaspcmd="mpirun -np $np $vaspexe"
# load pre-requisite modules
module load "${modules[@]}"
workdir=hf_scf

function run_vasp_hf_scf_calc () {
  raise_noexec "$vaspexe"
  raise_isdir "$workdir"
  reqs=(INCAR.pbe INCAR.coarse INCAR.hf KPOINTS.scf POTCAR POSCAR)
  raise_missing_prereq "${reqs[@]}"
  mkdir "$workdir"
  # process INCAR tags from variables
  sed "s/_encut_/$encut/g;s/_ediff_/$ediff/g;s/_prec_/$prec/g" INCAR.pbe > "$workdir/INCAR.pbe"
  sed "s/_encut_/$encut/g;s/_ediff_/$ediff/g;s/_prec_/$prec/g;s/_hfscreen_/$hfscreen/g" \
    INCAR.coarse > "$workdir/INCAR.coarse"
  sed -i "s/_nkredx_/$nkredx/g;s/_nkredy_/$nkredy/g;s/_nkredz_/$nkredz/g" "$workdir/INCAR.coarse"
  sed "s/_encut_/$encut/g;s/_hfscreen_/$hfscreen/g;s/_ediff_/$ediff/g;s/_prec_/$prec/g" INCAR.hf > "$workdir/INCAR.hf"
  cp KPOINTS.scf "$workdir/"
  
  if (( lthomas != 0 )); then
    s="AEXX = 1.0\nAGGAC = 1.0\nALDAC = 1.0\nLTHOMAS = T"
    echo -e "$s" >> "$workdir/INCAR.coarse"
    echo -e "$s" >> "$workdir/INCAR.hf"
  fi
  if (( use_damp != 0 )); then
    incar_change_tag "ALGO" "Damped" "$workdir/INCAR.coarse"
    incar_change_tag "ALGO" "Damped" "$workdir/INCAR.hf"
  fi

  dry=0
  if (( $# == 1 )); then
    dry=1
  fi
  cd "$workdir" || exit 1
  ln -s ../POSCAR POSCAR
  ln -s ../POTCAR POTCAR
  # start calculation
  if (( dry != 1 )); then
    run_hf_3steps "$vaspcmd"
  fi
  cd ..
}

function run_vasp_hf_scf_data () {
  return 1
}

function run_vasp_hf_scf_clean () {
  rm -rf "$workdir"
}

function run_vasp_hf_scf_help () {
  return 0
}

# ===== control function =====
function run_vasp_hf_scf () {
  opts=("$@")
  if (( $# == 0 )); then
    run_vasp_hf_scf_calc
  else
    case "${opts[0]}" in
      "help" | "-h" ) run_vasp_hf_scf_help "$0" ;;
      "clean" ) run_vasp_hf_scf_clean ;;
      "calc" | "-r" ) run_vasp_hf_scf_calc ;;
      "dry" | "-d" ) run_vasp_hf_scf_calc "dry" ;;
      "data" ) run_vasp_hf_scf_data "${opts[@]:1}" ;;
      * ) echo "Error: unknown options " "${opts[0]}"; \
        run_vasp_hf_scf_help "$0"; return 1;;
    esac
  fi
}

run_vasp_hf_scf "$@"

