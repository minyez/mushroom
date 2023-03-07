#!/usr/bin/env bash
# naming the workflow to prog_task_subtask
# and the control scripts to run_prog_task_subtask
# source custom variables and backend infrastructure
source ./variables.sh
source ./common.sh

np=${SLURM_NTASKS:=$defaultnp}
cmd="mpirun -np $np $vaspexe"
module load "${modules[@]}"
workdir="workdir"

function run_vasp_gw_wannier_help () {
  cat << EOF
Usage:
  $1 [calc | -r] : run
  $1 dry | -d    : dry run
  $1 data        : extract data
  $1 clean       : cleanup working directories
  $1 help | -h   : print this help message
EOF
}

function run_vasp_gw_wannier_calc () {
  reqs=()
  raise_missing_prereqs "${reqs[@]}"
  dry=0
  if (( $# == 1 )); then
    dry=1
  fi

  cd "$workdir" || exit 1
  if (( dry == 0 )); then
    $cmd
  fi
  cd ..
}

function run_vasp_gw_wannier_data () {
  # test argument parsing
  echo "$#"
}

function run_vasp_gw_wannier_plot () {
  # test argument parsing
  echo "$#"
}

function run_vasp_gw_wannier_clean () {
  rm -rf "$workdir"
}

# ===== control function =====
function run_vasp_gw_wannier () {
  opts=("$@")
  if (( $# == 0 )); then
    run_vasp_gw_wannier_calc
  else
    case "${opts[0]}" in
      "help" | "-h" ) run_vasp_gw_wannier_help "$0" ;;
      "calc" | "-r" ) run_vasp_gw_wannier_calc ;;
      "dry" | "-d" ) run_vasp_gw_wannier_calc "dry" ;;
      "data" ) run_vasp_gw_wannier_data "${opts[@]:1}" ;;
      "plot" | "-p" ) run_vasp_gw_wannier_plot "${opts[@]:1}" ;;
      "clean" ) run_vasp_gw_wannier_clean ;;
      *) echo "Error: unknown options " "${opts[0]}"; \
        run_vasp_gw_wannier_help "$0"; return 1 ;;
    esac
  fi
}

# start
run_vasp_gw_wannier "$@"

