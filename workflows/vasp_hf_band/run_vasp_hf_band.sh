#!/usr/bin/env bash

source ./variables.sh
source ./common.sh
source ./vasp.sh

workdir="hf_band"
np=${SLURM_NTASKS:=$defaultnp}
raise_noexec "$vaspexe"
vaspcmd="mpirun -np $np $vaspexe"

function run_vasp_hf_band_help () {
  cat << EOF
Usage:
  $0
  $0 data
  $0 clean
  $0 help | -h
EOF
}

function run_vasp_hf_band_clean () {
  rm -rf "$workdir"
}

function run_vasp_hf_band_calc () {
  module load "${modules[@]}"
  reqs=(INCAR.coarse INCAR.pbe KPOINTS.scf POSCAR POTCAR KPOINTS.scf KPOINTS.path)
  raise_missing_prereq "${reqs[@]}"
  raise_isdir "$workdir"
  
  mkdir -p "$workdir"
  cd "$workdir" || exit 2
  ln -s ../POTCAR POTCAR
  ln -s ../POSCAR POSCAR
  
  # Step 1 get KPOINTS for band calculation (very low parameter)
  sed "s/_encut_/100/g;s/_prec_/Low/g" ../INCAR.pbe > INCAR
  # STOPCAR for aborting calculation
  echo "LABORT = T; LSTOP = T" > STOPCAR
  cp ../KPOINTS.path KPOINTS
  $vaspcmd > .out 2>&1
  kpts_path=$(xml_kpts vasprun.xml)
  nkpt_path=$(echo "$kpts_path" | wc -l)
  cleanall
  # Step 2 get KPOINTS for scf calculation
  cp ../KPOINTS.scf KPOINTS
  $vaspcmd > .out 2>&1
  kpts_scf=$(xml_kpts_weigh vasprun.xml)
  nkpt_scf=$(echo "$kpts_scf" | wc -l)
  nkpt=$(( nkpt_path+nkpt_scf ))
  cleanall
  
  cat > KPOINTS.band << EOF
  Explicit kpoints for HF band structure
  $nkpt
  Reciprocal lattice
EOF
  echo "$kpts_scf" >> KPOINTS.band
  echo "$kpts_path" | awk '{print $0 "    0"}' >> KPOINTS.band
  cp KPOINTS.band KPOINTS.scf
  
  # Step 3 4 5: hf calculation with fixed charge
  rm -f STOPCAR INCAR
  run_hf_3steps_fixchg "$vaspcmd" "CHGCAR.hf"
}

function run_vasp_hf_band_data () {
  return
}

function run_vasp_hf_band () {
  opts=("$@")
  if (( $# == 0 )); then
    run_vasp_hf_band_calc
  fi
  case ${opts[0]} in
    "help" | "-h" ) run_vasp_hf_band_help "$0" ;;
    "data" ) run_vasp_hf_band_data ;;
    "clean" ) run_vasp_hf_band_clean ;;
    * ) echo "Unknown option:" "${opts[0]}"; exit 1 ;;
  esac
}

run_vasp_hf_band "$@"
