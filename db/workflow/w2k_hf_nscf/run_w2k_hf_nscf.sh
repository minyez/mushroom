#!/usr/bin/env bash
# source custom variables and backend infrastructure
source ./variables.sh
source ./common.sh

np=${SLURM_NTASKS:=$defaultnp}
cmd="mpirun -np $np $vaspexe"
module load "${modules[@]}"
workdir="workdir"

function run_w2k_hf_nscf_help () {
  cat << EOF
Usage:
  $1 [calc | -r] : run
  $1 dry | -d    : dry run
  $1 data        : extract data
  $1 clean       : cleanup working directories
  $1 help | -h   : print this help message
EOF
}

function run_w2k_hf_nscf_calc () {
  reqs=()
  raise_missing_prereq "${reqs[@]}"
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

function run_w2k_hf_nscf_data () {
  # test argument parsing
  echo "$#"
}

function run_w2k_hf_nscf_plot () {
  # test argument parsing
  echo "$#"
}

function run_w2k_hf_nscf_clean () {
  rm -rf "$workdir"
}

# ===== control function =====
function run_w2k_hf_nscf () {
  opts=("$@")
  if (( $# == 0 )); then
    run_w2k_hf_nscf_calc
  else
    case "${opts[0]}" in
      "help" | "-h" ) run_w2k_hf_nscf_help "$0" ;;
      "calc" | "-r" ) run_w2k_hf_nscf_calc ;;
      "dry" | "-d" ) run_w2k_hf_nscf_calc "dry" ;;
      "data" ) run_w2k_hf_nscf_data "${opts[@]:1}" ;;
      "plot" | "-p" ) run_w2k_hf_nscf_plot "${opts[@]:1}" ;;
      "clean" ) run_w2k_hf_nscf_clean ;;
      *) echo "Error: unknown options " "${opts[0]}"; \
        run_w2k_hf_nscf_help "$0"; return 1 ;;
    esac
  fi
}

# start
run_w2k_hf_nscf "$@"

