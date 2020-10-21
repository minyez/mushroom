#!/usr/bin/env bash
# naming the workflow to prog_task_subtask
# and the control scripts to run_prog_task_subtask
# source custom variables and backend infrastructure
source ./variables.sh
source ./common.sh
source ./vasp.sh

np=${SLURM_NTASKS:=$defaultnp}
vaspcmd="mpirun -np $np $vaspexe"
module load "${modules[@]}"
workdir="banddos"

function run_vasp_dft_banddos_help () {
  cat << EOF
Usage:
  $1 [calc | -r] : run
  $1 dry | -d    : dry run
  $1 data        : extract data
  $1 clean       : cleanup working directories
  $1 help | -h   : print this help message
EOF
}

function __setup_inputs () {
  sed "s/_encut_/$encut/g;s/_ediff_/$ediff/g;s/_prec_/$prec/g;s/_ispin_/$ispin/g;s/_sigma_/$sigma/g" \
    INCAR.scf > "$1/INCAR.scf"
  sed "s/_encut_/$encut/g;s/_ediff_/$ediff/g;s/_prec_/$prec/g;s/_ispin_/$ispin/g" \
    INCAR.dos > "$1/INCAR.dos"
  sed "s/_encut_/$encut/g;s/_ediff_/$ediff/g;s/_prec_/$prec/g;s/_ispin_/$ispin/g" \
    INCAR.band > "$1/INCAR.band"
  cp KPOINTS.scf "$1/KPOINTS.scf"
  cp KPOINTS.dos "$1/KPOINTS.dos"
  cp KPOINTS.band "$1/KPOINTS.band"
}

function __run_single () {
    cp "INCAR.$1" INCAR
    cp "KPOINTS.$1" KPOINTS
    $vaspcmd > "out.$1" 2>&1
    backup_results "$1"
}

function run_vasp_dft_banddos_calc () {
  reqs=(POSCAR POTCAR
        INCAR.scf INCAR.dos INCAR.band
        KPOINTS.scf KPOINTS.dos KPOINTS.band)
  raise_missing_prereq "${reqs[@]}"

  dry=0
  if (( $# == 1 )); then
    dry=1
  else
    raise_noexec "$vaspexe"
  fi

  raise_isdir "$workdir"
  mkdir -p "$workdir"
  cd "$workdir" || exit 1
  ln -s ../POSCAR POSCAR
  ln -s ../POTCAR POTCAR
  cd ..
  __setup_inputs "$workdir"

  if (( dry == 0 )); then
    cd "$workdir" || exit 1
    __run_single scf
    cp CHGCAR CHGCAR.scf

    __run_single dos
    warning_chgwav_change CHGCAR CHGCAR.scf

    __run_single band
    warning_chgwav_change CHGCAR CHGCAR.scf
    cd ..
  fi
}

function run_vasp_dft_banddos_data () {
  return 0
}

function run_vasp_dft_banddos_clean () {
  rm -rf dft_band dft_dos
}

# ===== control function =====
function run_vasp_dft_banddos () {
  opts=("$@")
  if (( $# == 0 )); then
    run_vasp_dft_banddos_calc
  else
    case "${opts[0]}" in
      "help" | "-h" ) run_vasp_dft_banddos_help "$0" ;;
      "calc" | "-r" ) run_vasp_dft_banddos_calc ;;
      "dry" | "-d" ) run_vasp_dft_banddos_calc "dry" ;;
      "data" ) run_vasp_dft_banddos_data "${opts[@]:1}" ;;
      "clean" ) run_vasp_dft_banddos_clean ;;
      *) echo "Error: unknown options " "${opts[0]}"; \
        run_vasp_dft_banddos_help "$0"; return 1 ;;
    esac
  fi
}

# start
run_vasp_dft_banddos "$@"

