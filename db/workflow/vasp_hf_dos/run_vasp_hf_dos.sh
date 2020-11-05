#!/usr/bin/env bash
# naming the workflow to prog_task_subtask
# and the control scripts to run_prog_task_subtask
# source custom variables and backend infrastructure
source ./variables.sh
source ./vasp.sh
source ./common.sh

np=${SLURM_NTASKS:=$defaultnp}
vaspcmd="mpirun -np $np $vaspexe"
module load "${modules[@]}"
workdir="hf_dos"

function run_vasp_hf_dos_help () {
  cat << EOF
Usage:
  $1 [calc | -r] : run
  $1 dry | -d    : dry run
  $1 data        : extract data
  $1 clean       : cleanup working directories
  $1 help | -h   : print this help message
EOF
}

function __setup_incars () {
  # copy INCARs
  sed "s/_encut_/$encut/g;s/_ediff_/$ediff/g;s/_prec_/$prec/g" \
    INCAR.pbe > "$1/INCAR.pbe"
  sed "s/_encut_/$encut/g;s/_ediff_/$ediff/g;s/_prec_/$prec/g;s/_hfscreen_/$hfscreen/g;" \
    INCAR.hf > "$1/INCAR.hf"
  incar_change_tag "PRECFOCK" "Fast" "$1/INCAR.hf" "$1/INCAR.coarse"
  if (( "$lthomas" == 1 )); then
    s="AEXX = 1.0\nAGGAC = 1.0\nALDAC = 1.0\nLTHOMAS = T"
    echo -e "$s" >> "$1/INCAR.coarse"
    echo -e "$s" >> "$1/INCAR.hf"
  fi
  # parallel setup
  kpar=$(largest_div_below_sqrt "$np")
  npar=$((np / kpar))
  for d in INCAR.pbe INCAR.coarse INCAR.hf; do
    #incar_change_tag "ICHARG" "11" "$1/$d"
    # ICHARG is controlled in run_hf_3steps_fixchg
    if (( np != 1 )); then
      incar_change_tag "NPAR" "$npar" "$1/$d"
      incar_change_tag "KPAR" "$kpar" "$1/$d"
    fi
  done
  if (( use_damp != 0 )); then
    incar_change_tag "ALGO" "Damped" "$1/INCAR.coarse"
    incar_change_tag "ALGO" "Damped" "$1/INCAR.hf"
  fi
}

function run_vasp_hf_dos_calc () {
  reqs=(POSCAR POTCAR KPOINTS.dos INCAR.pbe INCAR.hf)
  raise_missing_prereq "${reqs[@]}"
  raise_isdir "$workdir"
  mkdir -p "$workdir"

  dry=0
  if (( $# >= 1 )); then
    dry=1
  fi
  compute_chg=0
  if [[ ! -f "CHGCAR.hf" ]]; then
    compute_chg=1
  fi

  __setup_incars "$workdir"
  cp KPOINTS.dos "$workdir/KPOINTS.dos"

  cd "$workdir" || exit 1
  ln -s ../POSCAR POSCAR
  ln -s ../POTCAR POTCAR
  if (( dry == 0 )); then
    if (( compute_chg )); then
      if [[ ! -f ../KPOINTS.scf ]]; then
        echo "Error: provide KPOINTS.scf to compute CHGCAR from start"
        exit 1
      fi
      cp ../KPOINTS.scf KPOINTS.scf
      run_hf_3steps "$vaspcmd"
      mv CHGCAR ../CHGCAR.hf
    fi
    cp ../CHGCAR.hf CHGCAR.hf
    cp KPOINTS.dos KPOINTS.scf
    incar_change_tag "ISMEAR" -5 "INCAR.hf"
    incar_change_tag "NEDOS" 1200 "INCAR.hf"
    run_hf_3steps_fixchg "$vaspcmd" "CHGCAR.hf"
  fi
  cd ..
}

function run_vasp_hf_dos_data () {
  # test argument parsing
  echo "$#"
}

function run_vasp_hf_dos_plot () {
  # test argument parsing
  cd "$workdir" || exit 1
  m_vasp_dos -d DOSCAR.hf -o ../plotdos.agr "$@"
}

function run_vasp_hf_dos_clean () {
  rm -rf "$workdir"
}

# ===== control function =====
function run_vasp_hf_dos () {
  opts=("$@")
  if (( $# == 0 )); then
    run_vasp_hf_dos_calc
  else
    case "${opts[0]}" in
      "help" | "-h" ) run_vasp_hf_dos_help "$0" ;;
      "calc" | "-r" ) run_vasp_hf_dos_calc ;;
      "dry" | "-d" ) run_vasp_hf_dos_calc "dry" ;;
      "data" ) run_vasp_hf_dos_data "${opts[@]:1}" ;;
      "plot" | "-p" ) run_vasp_hf_dos_plot "${opts[@]:1}" ;;
      "clean" ) run_vasp_hf_dos_clean ;;
      *) echo "Error: unknown options " "${opts[0]}"; \
        run_vasp_hf_dos_help "$0"; return 1 ;;
    esac
  fi
}

# start
run_vasp_hf_dos "$@"

