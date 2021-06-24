#!/usr/bin/env bash
# source custom variables and backend infrastructure
source ./variables.sh
source ./common.sh
source ./w2k.sh

# variables conversion
np=${SLURM_NTASKS:=$defaultnp}
cmd="$runlapw"
(( np > 1 )) && cmd="$runlapw -p"
casename=$(get_casename)
workdir="$casename"
rkmax=${rkmax:=7}

if [[ -z "$ec" ]]; then
  if [[ -n "$ecev" ]]; then
    ec="$(ev2ry $ecev)"
  else
    echo "Set either ec or ecev in variables.sh!" && exit 1
  fi
fi
ec=$(printf "%.10f" "$ec")

module load "${modules[@]}"

function _write_inop () {
  # write inop input file
  cat > "$casename.inop" << EOF
  ${kpts_opt} 1       number of k-points, first k-point
-5.0 3.0 9999 Emin, Emax for matrix elements, NBvalMAX
${#op_choices[@]}             number of choices (columns in *outmat): 2: hex or tetrag. case
EOF
  for i in "${op_choices[@]}"; do
    echo " $i" >>  "$casename.inop"
  done
  echo "OFF           ON/OFF   writes MME to unit 4" >> "$casename.inop"
}

function _write_injoint () {
  # write inop input file
  # TODO custom for columns?
  cat > "$casename.injoint" << EOF
   1  9999                    : LOWER,UPPER and (optional) UPPER-VAL BANDINDEX
   0.0000    0.00100   1.0000 : EMIN DE EMAX FOR ENERGYGRID IN ryd
eV                            : output units  eV / ryd  / cm-1
   4                          : SWITCH, 4 for Im(EPSILON)
   3                          : NUMBER OF COLUMNS, 3 = Im xx, yy, zz
   0.1  0.1  0.3              : BROADENING (FOR DRUDE MODEL - switch 6,7 - ONLY)
EOF
}

function _write_inkram () {
  # write inkram input file
  cat > "$casename.inkram" << EOF
  ${kram_broad}    Gamma: broadening of interband spectrum
  ${kram_shift}    energy shift (scissors operator)
  0      add intraband contributions? yes/no: 1/0
EOF
}

function run_w2k_dft_optic_help () {
  cat << EOF
Usage:
  $1 run   : run optical calculation from SCF
  $1 data  : extract data
  $1 clean : cleanup working directories
  $1 help  : print this help message
EOF
}

function _scf () {
  # init and run SCF
  initlapw="$initlapw -b -numk $kpts_scf -rkmax $rkmax"
  [[ -n "$ecut" ]] && initlapw="$initlapw -ecut $ecut"
  $initlapw
  $cmd -ec "$ec" -i 60
  savelapw scf
}

function run_w2k_dft_optic_run () {
  dry=0
  (( $# == 1 )) && dry=1

  reqs=("$casename.struct")
  raise_missing_prereq "${reqs[@]}"
  [[ -d "$workdir" ]] && { echo "Working directory $workdir exists. Exit"; exit 2; }
  mkdir "$workdir"

  cd "$workdir" || exit 1
  cp ../"$casename.struct" .
  if (( dry == 0 )); then
    if [[ -f "$casename.clmsum" ]]; then
      echo "$casename.clmsum is found, skip SCF calculations"
    else
      _scf
    fi
  fi
  (( dry == 0 )) && { $x lapw0; xkgen_noshift "$x" $kpts_opt; $x lapw1; $x lapw2 -fermi; }
  _write_inop
  (( dry == 0 )) && $x optic
  _write_injoint
  (( dry == 0 )) && $x joint
  _write_inkram
  (( dry == 0 )) && $x kram
  cd ..
}

function run_w2k_dft_optic_data () {
  # test argument parsing
  echo "$#"
}

function run_w2k_dft_optic_plot () {
  # test argument parsing
  echo "$#"
}

function run_w2k_dft_optic_clean () {
  cd "$workdir" || exit 1
  # in w2k, one cleans the work directory instead of completely deleting it
  echo y | clean
}

# ===== control function =====
function run_w2k_dft_optic () {
  opts=("$@")
  if (( $# == 0 )); then
    run_w2k_dft_optic_run
  else
    case "${opts[0]}" in
      "help" | "-h" ) run_w2k_dft_optic_help "$0" ;;
      "run" ) run_w2k_dft_optic_run ;;
      "dry" | "-d" ) run_w2k_dft_optic_run "dry" ;;
#      "data" ) run_w2k_dft_optic_data "${opts[@]:1}" ;;
#      "plot" | "-p" ) run_w2k_dft_optic_plot "${opts[@]:1}" ;;
#      "clean" ) run_w2k_dft_optic_clean ;;
      *) echo "Error: unimplemented options " "${opts[0]}"; \
        run_w2k_dft_optic_help "$0"; return 1 ;;
    esac
  fi
}

# start
run_w2k_dft_optic "$@"

