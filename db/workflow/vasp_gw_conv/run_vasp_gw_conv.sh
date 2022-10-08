#!/usr/bin/env bash

# load pre-requisites from platform
# =====================
source ./variables.sh
source ./common.sh
source ./vasp.sh

np=${SLURM_NTASKS:=$defaultnp}
vaspcmd="mpirun -np $np $vaspexe"
[[ -n ${modules[*]} ]] && module load "${modules[@]}"

# ===== functions =====
function gw_calc () {
  run_gw_3steps "$vaspcmd"
  wall_time "OUTCAR.gw"
  rm -f ./*.tmp ./WAVE*
}

function run_vasp_gw_conv_help () {
  cat << EOF
Usage:
  $1 [calc | -r] : run convergence calculation for VASP GW
  $1 dry | -d    : dry run
  $1 data        : extract data to "vasp_gw_conv.dat"
  $1 clean       : cleanup all directories
  $1 help | -h   : print this help message
EOF
}

function run_vasp_gw_conv_calc () {
  dry=0
  if (( $# == 1 )); then
    dry=1
  fi
  raise_noexec "$vaspexe"
  reqs=(INCAR.scf INCAR.diag INCAR.gw POSCAR POTCAR KPOINTS.scf KPOINTS.gw)
  raise_missing_prereq "${reqs[@]}"

  for encut in "${encuts[@]}"; do
    # estimate number of bands from volume
    scale=$(poscar_scale "POSCAR")
    vol=$(triple_prod "$(poscar_latt_vec "POSCAR")")
    vol=$(echo "$vol $scale" | awk '{printf("%f\n", $1 * $2**3)}')
    nbandsmax=$(estimate_npw "$encut" "$vol")
    #nbandsmax=$(echo "$encut 750 1139" | awk '{printf("%d",0.5 + ($1/$2)**1.5 * $3)}')
    for encutgwratio in "${encutgwratios[@]}"; do
      # give ENCUTGW explicitly instead from a ratio of ENCUT
      if is_a_bigger_than_b "$encutgwratio" 3; then
        encutgw="$encutgw"
      else
        encutgw=$(echo "$encut $encutgwratio" | awk '{printf("%d", 0.5 + $1*$2)}')
      fi
      for nbandsratio in "${nbandsratios[@]}"; do
        # give nbands explicitly instead from a ratio of NPW
        if is_a_bigger_than_b "$nbandsratio" 1 ; then
          nbands="$nbandsratio"
        else
          nbands=$(echo "$nbandsmax $nbandsratio $np" | awk '{printf("%d",($1*$2) - ($1*$2) % $3)}')
        fi
        # skip zero bands
        if (( nbands == 0 )); then
          continue
        fi
        workdir="encut_${encut}_encutgw_${encutgw}_nbands_${nbands}"
        if [ -d "$workdir" ]; then
          continue
        fi
        mkdir -p "$workdir"

        sed "s/_encut_/$encut/g;s/_prec_/$prec/g" INCAR.scf \
          > "$workdir"/INCAR.scf
        sed "s/_encut_/$encut/g;s/_prec_/$prec/g;s/_nbands_/$nbands/g" INCAR.diag \
          > "$workdir"/INCAR.diag
        sed "s/_encut_/$encut/g;s/_prec_/$prec/g;s/_nbands_/$nbands/g;s/_encutgw_/$encutgw/g" INCAR.gw \
          > "$workdir"/INCAR.gw

        cd "$workdir" || exit 1
        ln -s ../POSCAR POSCAR
        ln -s ../POTCAR POTCAR
        cp ../KPOINTS.scf KPOINTS.scf
        cp ../KPOINTS.gw KPOINTS.gw
        if (( dry != 1 )); then
          wt=$(gw_calc 0)
          echo "ENCUT=$encut ENCUTGW=$encutgw NBANDS=$nbands computed, wall time = $wt"
        fi
        cd ..
      done
    done
  done
}

function run_vasp_gw_conv_clean () {
  rm -rf encut_*_encutgw_*_nbands_*/
}

function run_vasp_gw_conv_data () {
  case $# in
    0 ) cwd="./"; ik=1;;
    1 ) cwd="$1"; ik=1;;
    * ) cwd="$1"; ik="$2";;
  esac

  printf "%6s%8s%7s%12s%12s%12s%12s%12s%12s\n" \
    "#ENCUT" "ENCUTGW" "NBANDS" "EmaxGW" "EgGW" "QPC_VB" "QPC_CB" "UQPC_VB" "UQPC_CB"
  for d in "$cwd"/encut_*_encutgw_*_nbands_*; do
    encut=${d##*encut_}
    encut=${encut%%_encutgw_*}
    encutgw=${d##*_encutgw_}
    encutgw=${encutgw%%_nbands_*}
    nbands=${d##*_nbands_}
    if [[ "$nbands" != "*" ]] && [[ -f "$d/EIGENVAL.gw" ]] && [[ -f "$d/OUTCAR.gw" ]]; then
      gap=$(eigen_outcar_vbcb_ik "$d/EIGENVAL.gw" "$d/OUTCAR.gw" "$ik" | awk '{print($2-$1)}')
      emaxgw=$(awk "/ ${nbands} / {print \$2}" "$d/EIGENVAL.gw" | sort | tail -1)
      qpdata=()
      split_str qpdata "$(outcar_qpc_vb_cb "$d/OUTCAR.gw" "${@:2}")"
      printf "%6d%8d%7d%12.5f%12.5f%12.5f%12.5f%12.5f%12.5f\n" \
        "$encut" "$encutgw" "$nbands" "$emaxgw" "$gap" "${qpdata[@]}"
    fi
  done
}

# ===== control function =====
function run_vasp_gw_conv () {
  opts=("$@")
  if (( $# == 0 )); then
    run_vasp_gw_conv_calc
  else
    case "${opts[0]}" in
      "help" | "-h" ) run_vasp_gw_conv_help "$0" ;;
      "calc" | "-r" ) run_vasp_gw_conv_calc ;;
      "dry" | "-d" ) run_vasp_gw_conv_calc "dry" ;;
      "data" ) run_vasp_gw_conv_data "${opts[@]:1}" ;;
      "clean" ) run_vasp_gw_conv_clean ;;
      *) echo "Error: unknown options " "${opts[0]}";\
        run_vasp_gw_conv_help "$0"; return 1 ;;
    esac
  fi
}

run_vasp_gw_conv "$@"

