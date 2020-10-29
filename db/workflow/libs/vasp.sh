#!/usr/bin/env bash

# common functions to be used in vasp workflows
function warning_chgwav_change () {
  # warning when two CHGCAR/WAVECAR files are different, used for sanity check of band calculation
  # $1 $2 : paths of CHGCAR/WAVECAR files
  # this may often happen in between spin-polarizd calculations
  chgwav1=$1
  chgwav2=$2
  if [[ -n $(diff -q "$chgwav1" "$chgwav2") ]]; then
    echo "WARNING!!! CHGCAR/WAVECAR might change during calculation"
  fi
}

function backup_results () {
  # back up result files
  files=(OUTCAR EIGENVAL DOSCAR PROCAR vasprun.xml OSZICAR
         ELFCAR LOCPOT)
  for f in "${files[@]}"; do
    if [ -f "$f" ]; then
      cp "$f" "$f.$1"
    fi
  done
}

function clean () {
  # clean all result and temporary files. back up those you need before you do
  rm -f IBZKPT XDATCAR CONTCAR PROCAR OUTCAR OSZICAR vasprun.xml \
    REPORT ELFCAR LOCPOT PCDAT DOSAR EIGENVAL CHG W*.tmp
}

function cleanall () {
  # clean all result, temporary and restart files (WAVECAR, WAVEDER, CHGCAR)
  clean
  rm -f CHGCAR WAVECAR WAVEDER WAVECAR.chi
}

function wall_time () {
  # get wall time from OUTCAR
  # $1: outcar file (OUTCAR)
  if (( $# == 0 )); then
    fn="OUTCAR"
  else
    fn=$1
  fi
  awk '/Elapsed time/ {print $4}' "$fn"
}

function outcar_nelect () {
  # get the number of electrons (float)
  # $1: outcar file (OUTCAR)
  case $# in
    0 ) fn="OUTCAR";;
    * ) fn=$1;;
  esac
  awk '/NELECT/ {print $3}' "$fn"
}

function outcar_vb () {
  # get the number of valence bands
  # $1: outcar file (OUTCAR)
  case $# in
    0 ) fn="OUTCAR";;
    * ) fn=$1;;
  esac
  awk '/NELECT/ {printf("%d", $3/2.0)}' "$fn"
}

function outcar_totene () {
  case $# in
    0 ) outcar="OUTCAR"; iostep=1;;
    1 ) outcar="$1"; iostep=1;;
    * ) outcar="$1"; iostep=$2;;
  esac
  grep -m "$iostep" 'energy  without' "$outcar" | tail -1 | awk '{print $7}' 
}

function outcar_nbands () {
  # get the total number of bands
  # $1: outcar file (OUTCAR)
  case $# in
    0 ) fn="OUTCAR";;
    * ) fn=$1;;
  esac
  awk '/NBANDS/ {print $15}' "$fn"
}

function eigen_outcar_vbcb_ik () {
  # get the vb and cb eigen values at ik from eigenvalue file
  #
  # 1 arguments: index of k
  # 2 arguments: eigen file and index of k
  # 3 or more arguments:
  #   $1: eigen value file (EIGENVAL)
  #   $2: outcar file (OUTCAR)
  #   $3: index of k (1)
  #
  # returns: vb energy and cb energy at ik
  case $# in
    0 ) fneig="EIGENVAL"; fnout="OUTCAR"; ik=1;;
    1 ) fneig="EIGENVAL"; fnout="OUTCAR"; ik=$1;;
    2 ) fneig="$1"; fnout="OUTCAR"; ik=$2;;
    * ) fneig="$1"; fnout="$2"; ik=$3;;
  esac
  vb=$(outcar_vb "$fnout")
  nbs=$(outcar_nbands "$fnout")
  vbln=$(( (nbs+2)*(ik-1)+vb+8))
  cbln=$(( vbln+1 ))
  vb=$(awk "FNR == $vbln {print \$2}" "$fneig")
  cb=$(awk "FNR == $cbln {print \$2}" "$fneig")
  echo "$vb $cb"
}

function outcar_qpc_vb_cb () {
  # get the QP correction of VBM and CBM
  # $1: OUTCAR file
  # $2: index of kpoints
  # returns: qpc (VB), qpc (CB), unscaled QPC (VB), unscaled QPC (CB)
  case $# in
    0 ) fn="OUTCAR"; ik=1;;
    1 ) fn="$1"; ik=1;;
    * ) fn="$1"; ik=$2;;
  esac

  vb=$(outcar_vb "$fn")
  ln=$(grep -n -m "$ik" "band No.  KS-energies  QP-energies" "$fn" | tail -1 | awk '{print $1}')
  ln="${ln/:/}"
  
  vbln=$(( ln + vb + 1 ))
  cbln=$(( vbln + 1 ))
  
  qpc_vb=$(awk "FNR == $vbln {print(\$3-\$2)}" "$fn")
  qpc_cb=$(awk "FNR == $cbln {print(\$3-\$2)}" "$fn")
  uqpc_vb=$(awk "FNR == $vbln {print(\$4-\$5)}" "$fn")
  uqpc_cb=$(awk "FNR == $cbln {print(\$4-\$5)}" "$fn")

  echo "$qpc_vb $qpc_cb $uqpc_vb $uqpc_cb"
}

function run_hf_3steps () {
  vaspcmd=$1
  # step 1: PBE preconverge
  cp KPOINTS.scf KPOINTS
  cp INCAR.pbe INCAR
  $vaspcmd > out.pbe 2>&1
  backup_results pbe
  # step 2: coarse hf calculation
  cp INCAR.coarse INCAR
  $vaspcmd > out.coarse 2>&1
  backup_results coarse
  # step 3: accurate hf calculation
  cp INCAR.hf INCAR
  $vaspcmd > out.hf 2>&1
  backup_results hf
}

function run_hf_3steps_fixchg () {
  vaspcmd=$1
  scfchg=$2
  cp -f "$scfchg" CHGCAR
  # step 1: PBE SCF for preconvergence
  cp KPOINTS.scf KPOINTS
  cp INCAR.pbe INCAR
  incar_change_tag "ICHARG" 11
  $vaspcmd > out.pbe 2>&1
  warning_chgwav_change "$scfchg" "CHGCAR"
  backup_results pbe
  # step 2: coarse hf calculation with fixed charge
  cp INCAR.coarse INCAR
  incar_change_tag "ISTART" 1
  incar_change_tag "ICHARG" 11
  $vaspcmd > out.coarse 2>&1
  warning_chgwav_change "$scfchg" "CHGCAR"
  backup_results coarse
  # step 3: accurate hf calculation
  cp INCAR.hf INCAR
  incar_change_tag "ISTART" 1
  incar_change_tag "ICHARG" 11
  $vaspcmd > out.hf 2>&1
  warning_chgwav_change "$scfchg" "CHGCAR"
  backup_results hf
}

function run_hf_4steps_fixchg_dos () {
  vaspcmd=$1
  scfchg=$2
  cp -f "$scfchg" CHGCAR
  # step 1: PBE SCF for preconvergence
  cp KPOINTS.scf KPOINTS
  cp INCAR.pbe INCAR
  incar_change_tag "ICHARG" 11
  $vaspcmd > out.pbe 2>&1
  warning_chgwav_change "$scfchg" "CHGCAR"
  backup_results pbe
  # step 2: coarse hf calculation with fixed charge
  cp INCAR.coarse INCAR
  incar_change_tag "ISTART" 1
  incar_change_tag "ICHARG" 11
  $vaspcmd > out.coarse 2>&1
  warning_chgwav_change "$scfchg" "CHGCAR"
  backup_results coarse
  # step 3: preconverging hf calculation with Gaussian smearing
  cp INCAR.hf INCAR
  incar_change_tag "ISTART" 1
  incar_change_tag "ISMEAR" 0
  incar_change_tag "ICHARG" 11
  $vaspcmd > out.hf 2>&1
  warning_chgwav_change "$scfchg" "CHGCAR"
  backup_results hf
  # step 4: hf calculation with damped (IALGO=53) and Bloechls tetrahedron
  cp INCAR.hf INCAR
  incar_change_tag "ISTART" 1
  incar_change_tag "ISMEAR" -5
  incar_change_tag "ICHARG" 11
  incar_change_tag "ALGO" "Damped"
  $vaspcmd > out.hf_damped 2>&1
  warning_chgwav_change "$scfchg" "CHGCAR"
  backup_results hf_damped
}
function run_gw_3steps () {
  # run the three step GW calculations
  # $1: vasp command, e.g. mpirun -np 4 vasp
  # $2: starting step. 2 to skip SCF, 3 to skip Diag
  vaspcmd=$1
  doscf=1
  dodiag=1
  if (( $# == 2 )); then
    if (( $2 >= 2 )); then
      doscf=0
    fi
    if (( $2 >= 3 )); then
      dodiag=0
    fi
  fi
  # 1. SCF: compute charge
  if (( doscf == 1 )); then
    cp INCAR.scf INCAR
    cp KPOINTS.scf KPOINTS
    $vaspcmd > out.scf 2>&1
    backup_results scf
  fi
  # 2. Diagonalization
  if (( dodiag == 1 )); then
    cp INCAR.diag INCAR
    cp KPOINTS.gw KPOINTS
    $vaspcmd > out.diag 2>&1
    backup_results diag
  fi
  # 3. GW
  cp INCAR.gw INCAR
  $vaspcmd > out.gw 2>&1
  backup_results gw
}

function incar_encut () {
  if (( $# == 0 )); then
    fn="INCAR"
  else
    fn=$1
  fi
  s=$(awk '/ENCUT[ ]*=/' "$fn")
  s=${s#*"="[ ]*}
  s=${s%%[ ]*";"*}
  echo "$s"
}

function xml_kpts () {
  # print kpoint list from vasprun.xml
  # $1 : path of vasprun.xml file
  vaspxml=$1
  if [[ ! -f "$vaspxml" ]]; then
    exit 1
  fi
  lnkpt=$(grep -n -m 1 "<varray name=\"kpointlist\" >" "$vaspxml" | tail -1 | awk '{print $1}')
  lnkpt="${lnkpt/:/}"
  lnwei=$(grep -n -m 1 "<varray name=\"weights\" >" "$vaspxml" | tail -1 | awk '{print $1}')
  lnwei="${lnwei/:/}"
  kpts=$(awk "FNR < $(( lnwei-1 ))&& FNR > $lnkpt {printf(\"%.8f   %.8f   %.8f\n\", \$2, \$3, \$4)}" "$vaspxml")
  echo "$kpts"
}

function xml_kpts_weigh () {
  # print kpoints list and integer weights from vasprun.xml
  # $1 : path of vasprun.xml file
  # $2 (optional) : index of Gamma point to get the number of kpoints in BZ
  # TODO automatic the process of getting the number of kpoints in BZ
  case $# in
    0 ) vaspxml="vasprun.xml"; gamma=1;;
    1 ) vaspxml="$1"; gamma=1;;
    * ) vaspxml="$1"; gamma=$2;;
  esac

  kpts=$(xml_kpts "$vaspxml")
  nkpt=$(echo "$kpts" | wc -l)
  lnwei=$(grep -n -m 1 "<varray name=\"weights\" >" "$vaspxml" | tail -1 | awk '{print $1}')
  lnwei="${lnwei/:/}"
  nkall=$(awk "FNR == $(( lnwei+gamma )) {print int(1.0 / \$2 + 0.1)}" "$vaspxml")
  weigh=$(awk "FNR <= $(( lnwei+nkpt ))&& FNR > $lnwei {print int($nkall * \$2 + 0.1)}" "$vaspxml")
  echo "$kpts" > .kpts.tmp; echo "$weigh" > .weigh.tmp; paste .kpts.tmp .weigh.tmp
  rm -f .kpts.tmp .weigh.tmp
}

function poscar_latt_vec () {
  case $# in
    0 ) poscar="POSCAR";;
    * ) poscar="$1";;
  esac
  awk 'FNR<6 && FNR>2 {printf("%s ", $0)}' "$poscar"
  echo ""
}

function poscar_scale () {
  # get scale factor of POSCAR structure
  case $# in
    0 ) poscar="POSCAR";;
    * ) poscar="$1";;
  esac
  awk 'FNR==2 {printf("%f ", $0)}' "$poscar"
  echo ""
}

function incar_change_tag () {
  # change one tag of INCAR
  case $# in
    2 ) tag="$1"; value="$2"; incar="INCAR"; unset incarout;;
    3 ) tag="$1"; value="$2"; incar="$3"; unset incarout;;
    4 ) tag="$1"; value="$2"; incar="$3"; incarout="$4";;
    * ) echo "Error! specify tag and value"; exit 1;;
  esac
  if grep "$tag =" "$incar"; then
    n=$(grep -n "$tag = " "$incar" | awk '{print $1}')
    n="${n%%:*}"
    if [[ -z ${incarout+1} ]]; then
      sed -i -e "/$tag = /a $tag = $value" -e "${n}d" "$incar"
    else
      sed -e "/$tag = /a $tag = $value" -e "${n}d" "$incar" > "$incarout"
    fi
  else
    if [[ -z ${incarout+1} ]]; then
      echo "$tag = $value" >> "$incar"
    else
      cp "$incar" "$incarout"
      echo "$tag = $value" >> "$incarout"
    fi
  fi
}

function incar_delete_tag () {
  # delete tag in INCAR
  case $# in
    1 ) tag="$1"; incar="INCAR"; unset incarout;;
    2 ) tag="$1"; incar="$3"; unset incarout;;
    3 ) tag="$1"; incar="$3"; incarout="$4";;
    * ) echo "Error! specify tag and value"; exit 1;;
  esac
  if grep "$tag =" "$incar"; then
    if [[ -z ${incarout+1} ]]; then
      sed -i "/$tag = /d" "$incar"
    else
      sed "/$tag = /d" "$incar" > "$incarout"
    fi
  else
    # tag to delete is not found.
    # directly copy the original INCAR to new place
    if [[ -n ${incarout+1} ]]; then
      cp "$incar" "$incarout"
    fi
  fi
}

function incar_add_npar_kpar () {
  case $# in
    2 ) npar="$1"; kpar="$2"; incar="INCAR" ;;
    * ) npar="$1"; kpar="$2"; incar="$3" ;;
  esac
  if (( npar != 1 )); then
    incar_change_tag "NPAR" "$npar" "$incar"
  fi
  if (( kpar != 1 )); then
    incar_change_tag "KPAR" "$kpar" "$incar"
  fi
}

