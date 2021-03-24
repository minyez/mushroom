#!/usr/bin/env bash

source ./variables.sh
source ./common.sh
source ./vasp.sh

np=${SLURM_NTASKS:=$defaultnp}
vaspcmd="mpirun -np $np $vaspexe"
# load pre-requisite modules
module load "${modules[@]}"

function run_vasp_hf_conv_data () {
  case $# in
    0 ) cwd="./"; ik=1 ;;
    1 ) cwd="$1"; ik=1 ;;
    * ) cwd="$1"; ik="$2" ;;
  esac

  printf "%6s%9s%15s%9s%9s%9s\n" "#ENCUT" "kmesh" "Etot" "CBM" "VBM" "Egap"
  for d in "$cwd"/encut_*_kmesh_*; do
    encut=${d##*encut_}
    encut=${encut%%_kmesh_*}
    kmesh=${d##*_kmesh_}
    eigenf="$d/EIGENVAL.hf"
    outcarf="$d/OUTCAR.hf"
    if [[ "$kmesh" != "*" ]] && [[ -f "$eigenf" ]] && [[ -f "$outcarf" ]]; then
      etot=$(outcar_totene "$outcarf")
      if [[ "$ik" == "min" ]]; then
        gap=0
      else
        edges=$(eigen_outcar_vbcb_ik "$eigenf" "$outcarf" "$ik")
        cbm=${edges##* }
        vbm=${edges%% *}
        gap=$(echo "$cbm $vbm" | awk '{print($1-$2)}')
      fi
      printf "%6s%9s%15.9f%9.5f%9.5f%9.5f\n" "$encut" "$kmesh" "$etot" "$cbm" "$vbm" "$gap"
    fi
  done
}

function run_vasp_hf_conv_calc () {
  raise_noexec "$vaspexe"
  reqs=(INCAR.pbe INCAR.hf POTCAR POSCAR)
  raise_missing_prereq "${reqs[@]}"
  dry=0
  if (( $# == 1 )); then
    dry=1
  fi
  kpar=$(largest_div_below_sqrt "$np")
  npar=$((np / kpar))

  for ie in "${!encuts[@]}"; do
    encut="${encuts[ie]}"
    for ik in "${!kmeshes[@]}"; do
      kmesh="${kmeshes[ik]}"
      if (( ik == 0 )) || (( ie == 0 )); then
        workdir="encut_${encut}_kmesh_${kmesh// /-}"
        if [ -d "$workdir" ]; then
          continue
        fi
        mkdir -p "$workdir"
        sed "s/_encut_/$encut/g;s/_ediff_/$ediff/g;s/_prec_/$prec/g" \
          INCAR.pbe > "$workdir/INCAR.pbe"
        sed "s/_encut_/$encut/g;s/_ediff_/$ediff/g;s/_prec_/$prec/g;s/_hfscreen_/$hfscreen/g;" \
          INCAR.hf > "$workdir/INCAR.hf"
        for d in INCAR.pbe INCAR.hf; do
          incar_add_npar_kpar "$npar" "$kpar" "$workdir/$d"
        done
        if [[ -n "$aexx" ]]; then
          incar_change_tag "AEXX" "$aexx" "$workdir/INCAR.hf"
        fi
        if (( lthomas != 0 )); then
          s="AGGAC = 1.0 ; ALDAC = 1.0 ; LTHOMAS = T"
          echo "$s" >> "$workdir/INCAR.hf"
          incar_change_tag "AEXX" 1.0 "$workdir/INCAR.hf"
        fi
        if (( use_damp != 0 )); then
          incar_change_tag "ALGO" "Damped" "$workdir/INCAR.hf"
        fi
        sed "s/PRECFOCK = Normal/PRECFOCK = Fast/g" "$workdir/INCAR.hf" > "$workdir/INCAR.coarse"
        cat > "$workdir/KPOINTS.scf" << EOF
kpoints for hf convergence
0
G
$kmesh
0 0 0
EOF
        cd "$workdir" || exit 1
        ln -s ../POSCAR POSCAR
        ln -s ../POTCAR POTCAR
        if (( dry == 0 )); then
          run_hf_3steps "$vaspcmd"
          wt=$(wall_time "OUTCAR.hf")
          echo "ENCUT=$encut kmesh=${kmesh// /-} computed, wall time = $wt"
        fi
        cd ..
      fi
    done
  done
}

function run_vasp_hf_conv_clean () {
  rm -rf encut_*_kmesh_*
}

function run_vasp_hf_conv_help () {
  cat << EOF
Usage:
  $1 [calc | -r]         : run convergence calculation for VASP hybrid functional
  $1 dry | -d            : dry run
  $1 data [dir] [ik|min] : extract hf data
  $1 clean               : cleanup all working directories "encut_*_kmesh_*"
  $1 help | -h           : print this help message
EOF
}

# ===== control function =====
function run_vasp_hf_conv () {
  opts=("$@")
  if (( $# == 0 )); then
    run_vasp_hf_conv_calc
  else
    case "${opts[0]}" in
      "help" | "-h" ) run_vasp_hf_conv_help "$0";;
      "clean" ) run_vasp_hf_conv_clean;;
      "calc" | "-r" ) run_vasp_hf_conv_calc;;
      "dry" | "-d" ) run_vasp_hf_conv_calc "dry";;
      "data" ) run_vasp_hf_conv_data "${opts[@]:1}";;
      * ) echo "Error: unknown options " "${opts[0]}"; \
        run_vasp_hf_conv_help "$0"; return 1;;
    esac
  fi
}

run_vasp_hf_conv "$@"

