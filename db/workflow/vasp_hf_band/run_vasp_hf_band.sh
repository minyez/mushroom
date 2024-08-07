#!/usr/bin/env bash

source ./variables.sh
source ./common.sh
source ./vasp.sh

workdir="hf_band"
np=${SLURM_NTASKS:=$defaultnp}
vaspcmd="mpirun -np $np $vaspexe"

function run_vasp_hf_band_help () {
  cat << EOF
Usage:
  $1 [calc | -r]
  $1 data
  $1 plot
  $1 dry | -d
  $1 clean
  $1 help | -h
EOF
}

function run_vasp_hf_band_clean () {
  rm -rf "$workdir"
}

function __setup_incars () {
  # copy INCARs
  sed "s/_encut_/$encut/g;s/_ediff_/$ediff/g;s/_prec_/$prec/g" \
    INCAR.pbe > "$1/INCAR.pbe"
  sed "s/_encut_/$encut/g;s/_ediff_/$ediff/g;s/_prec_/$prec/g;s/_hfscreen_/$hfscreen/g;" \
    INCAR.hf > "$1/INCAR.hf"
  if (( lthomas != 0 )); then
    s="AEXX = 1.0\nAGGAC = 1.0\nALDAC = 1.0\nLTHOMAS = T"
    echo -e "$s" >> "$1/INCAR.hf"
  fi
  if (( use_damp != 0 )); then
    incar_change_tag "ALGO" "Damped" "$1/INCAR.hf"
  fi
  if [[ -n "$aexx" ]]; then
    incar_change_tag "AEXX" "$aexx" "$1/INCAR.hf"
  fi
  # parallel setup
  kpar=$(largest_div_below_sqrt "$np")
  npar=$((np / kpar))
  for d in INCAR.pbe INCAR.hf; do
    incar_add_npar_kpar "$npar" "$kpar" "$1/$d"
  done

  if [ -f CHGCAR.hf ]; then
    for d in INCAR.pbe INCAR.hf; do
      incar_change_tag "ICHARG" "11" "$1/$d"
    done
  fi
  #sed "s/PRECFOCK = Normal/PRECFOCK = Fast/g" "$workdir/INCAR.hf" > "$workdir/INCAR.coarse"
  incar_change_tag "PRECFOCK" "Fast" "$1/INCAR.hf" "$1/INCAR.coarse"
}

function run_vasp_hf_band_calc () {
  module load "${modules[@]}"
  reqs=(INCAR.pbe KPOINTS.scf POSCAR POTCAR KPOINTS.scf KPOINTS.path)
  raise_missing_prereq "${reqs[@]}"
  raise_isdir "$workdir"
  raise_noexec "$vaspexe"
  dry=0
  if (( $# != 0 )); then
    dry=1
  fi
  
  mkdir -p "$workdir"
  __setup_incars "$workdir"
  if [ -f CHGCAR.hf ]; then
    cp CHGCAR.hf "$workdir/"
  fi

  cd "$workdir" || exit 2
  ln -s ../POTCAR POTCAR
  ln -s ../POSCAR POSCAR

  cp ../KPOINTS.path KPOINTS
  # get KPOINTS for band calculation (very low parameter)
  sed "s/_encut_/100/g;s/_prec_/Low/g;s/_ediff_/1e-2/g" ../INCAR.pbe > INCAR
  # STOPCAR for aborting calculation
  echo "LABORT = T; LSTOP = T" > STOPCAR
  $vaspcmd > .out 2>&1
  kpts_path=$(xml_kpts vasprun.xml)
  nkpt_path=$(echo "$kpts_path" | wc -l)
  cleanall
  # Step 2 get KPOINTS for scf calculation
  cp ../KPOINTS.scf KPOINTS
  $vaspcmd > .out 2>&1
  cp IBZKPT KPOINTS.scf_ibzkpt
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
  rm -f STOPCAR INCAR KPOINTS
  
  # Step 3 4 5: hf calculation
  if (( dry == 0 )); then
    if [ -f CHGCAR.hf ]; then
      run_hf_3steps_fixchg "$vaspcmd" "CHGCAR.hf"
    else
      run_hf_3steps "$vaspcmd"
    fi
  fi
}

function run_vasp_hf_band_data () {
  echo "not implemented"
  exit 1
}

function run_vasp_hf_band_plot () {
  # plot partial wave to agr
  cd "$workdir" || exit 1
  removek=$(awk 'FNR == 2' KPOINTS.scf_ibzkpt)
  echo "plotting at directory $workdir with:"
  echo "    m_vasp_pwav -p PROCAR.hf -o ../plotpwav.agr --removek $removek" "$@"
  m_vasp_pwav -p PROCAR.hf -o ../plotpwav.agr --removek "$removek" "$@"
  echo "Graceplot written to plotpwav.agr"
}

function run_vasp_hf_band () {
  opts=("$@")
  if (( $# == 0 )); then
    run_vasp_hf_band_calc
  else
    case ${opts[0]} in
      "calc" | "-r" ) run_vasp_hf_band_calc ;;
      "dry" | "-d" ) run_vasp_hf_band_calc dry ;;
      "help" | "-h" ) run_vasp_hf_band_help "$0" ;;
      "plot" ) run_vasp_hf_band_plot "${opts[@]:1}";;
      "data" ) run_vasp_hf_band_data "${opts[@]:1}";;
      "clean" ) run_vasp_hf_band_clean ;;
      * ) echo "Error: unknown option " "${opts[0]}"; \
        run_vasp_hf_band_help "$0"; exit 1 ;;
    esac
  fi
}

run_vasp_hf_band "$@"

