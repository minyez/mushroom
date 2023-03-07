#!/usr/bin/env bash
# source custom variables and backend infrastructure
source ./variables.sh
source ./common.sh

np=${SLURM_NTASKS:=$defaultnp}
if [[ -n "$gapdir" ]]; then
  gapdir="${gapdir%%/}/"
fi
if [[ -z "$gapinit" ]]; then
  gapinit="${gapdir}gap${gapver}_init"
fi
if [[ -z "$gapexe" ]]; then
  if (( np > 1 )); then
    gapexe="${gapdir}gap${gapver}-mpi.x"
  else
    gapexe="${gapdir}gap${gapver}.x"
  fi
fi
if (( np > 1 )); then
  gapcmd="mpirun -np $np ${gapexe}"
else
  gapcmd="${gapexe}"
fi

module load "${modules[@]}"

function run_gap_nlo_conv_help () {
  cat << EOF
Usage:
  $1 submit      : submit each HLOs setup to HPC
  $1 init        : initialize inputs and job script
  $1 dry | -d    : dry run
  $1 data        : extract data
  $1 clean       : cleanup working directories
  $1 help | -h   : print this help message
EOF
}

function run_gap_nlo_conv_init () {
  raise_noexec "$gapinit"
  # a directory named as casename is required
  reqs=("$casename")
  raise_missing_dir "${reqs[@]}"
  dry=0
  if (( $# == 1 )); then
    dry=1
  fi

  workdir="workdir"
  cd "$workdir" || exit 1
  if (( dry == 0 )); then
    $gapcmd
  fi
  cd ..
}

function run_gap_nlo_conv_data () {
  # test argument parsing
  case $# in
    0 ) cwd="./"; ik=1;;
    1 ) cwd="$1"; ik=1;;
    * ) cwd="$1"; ik="$2";;
  esac

  printf "%4s%8s%7s%12s%12s%12s%12s%12s\n" \
    "#nlo" "delta-l" "KSGAP" "G0W0GAP" "GW0GAP" "QPC_CB" "UQPC_VB" "UQPC_CB"
  for d in "$cwd"/nlo_*-p_*; do
    p=${d##*-p_}
    nlo=${d%%-p_*}
    nlo=${nlo##*nlo_}
    if [[ "$nlo" != "*" ]] && [[ "$p" != "*" ]] && [[ -f "$d/$casename.outgw" ]] && [[ -f "$d/$casename.eqpeV_GW" ]]; then
      echo
    #  gap=$(eigen_outcar_vbcb_ik "$d/EIGENVAL.gw" "$d/OUTCAR.gw" "$ik" | awk '{print($2-$1)}')
    #  qpdata=()
    #  split_str qpdata "$(outcar_qpc_vb_cb "$d/OUTCAR.gw" "${@:2}")"
    #  printf "%6d%8d%7d%12.5f%12.5f%12.5f%12.5f%12.5f\n" \
    #    "$encut" "$encutgw" "$nbands" "$gap" "${qpdata[@]}"
    fi
  done
}

function run_gap_nlo_conv_submit () {
  # test argument parsing
  echo "$#"
}

function run_gap_nlo_conv_plot () {
  # test argument parsing
  echo "$#"
}

function run_gap_nlo_conv_clean () {
  # test argument parsing
  echo "$#"
}

# ===== control function =====
function run_gap_nlo_conv () {
  opts=("$@")
  if (( $# == 0 )); then
    run_gap_nlo_conv_init
  else
    case "${opts[0]}" in
      "help" | "-h" ) run_gap_nlo_conv_help "$0" ;;
      "init" ) run_gap_nlo_conv_init ;;
      "submit" ) run_gap_nlo_conv_submit ;;
      "dry" | "-d" ) run_gap_nlo_conv_init "dry" ;;
      "data" ) run_gap_nlo_conv_data "${opts[@]:1}" ;;
      "plot" | "-p" ) run_gap_nlo_conv_plot "${opts[@]:1}" ;;
      "clean" ) run_gap_nlo_conv_clean ;;
      *) echo "Error: unknown options " "${opts[0]}"; \
        run_gap_nlo_conv_help "$0"; return 1 ;;
    esac
  fi
}

# start
run_gap_nlo_conv "$@"

