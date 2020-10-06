#!/usr/bin/env bash
# common functions to be used in vasp workflows
function raise_chgcar_change () {
  # raise when two CHGCAR files are different, used for sanity check of band calculation
  # $1 $2 : paths of CHGCAR files
  chg1=$1
  chg2=$2
  if [[ -n $(diff -q "$chg1" "$chg2") ]]; then
    echo "Unexpected CHGCAR change during band calculation."; exit 1
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
    REPORT ELFCAR LOCPOT PCDAT DOCAR EIGENVAL CHG W*.tmp
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
  if (( $# == 0 )); then
    fn="OUTCAR"
  else
    fn=$1
  fi
  awk '/NELECT/ {print $3}' "$fn"
}

function outcar_vb () {
  # get the number of valence bands
  # $1: outcar file (OUTCAR)
  if (( $# == 0 )); then
    fn="OUTCAR"
  else
    fn=$1
  fi
  awk '/NELECT/ {printf("%d", $3/2.0)}' "$fn"
}

function outcar_nbands () {
  # get the total number of bands
  # $1: outcar file (OUTCAR)
  if (( $# == 0 )); then
    fn="OUTCAR"
  else
    fn=$1
  fi
  awk '/NBANDS/ {print $15}' "$fn"
}

function eig_outcar_eigen_ik () {
  # get the vb and cb eigen values at ik
  # $1: index of k (1)
  # $2: eigen value file (EIGENVAL)
  # $3: outcar file (OUTCAR)
  # returns: vb energy and cb energy at ik
  if (( $# == 3 )); then
    ik=$1
    fneig=$2
    fnout=$3
  elif (( $# == 2 )); then
    ik=$1
    fneig=$2
    fnout="OUTCAR"
  elif (( $# == 1 )); then
    ik=$1
    fneig="EIGENVAL"
    fnout="OUTCAR"
  else
    ik=1
    fneig="EIGENVAL"
    fnout="OUTCAR"
  fi
  vb=$(get_vb "$fnout")
  nbs=$(get_nbands "$fnout")
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
  fn=$1
  ik=1
  if (( $# == 2 )); then
    ik=$2
  fi

  vb=$(get_vb "$fn")
  ln=$(grep -n -m "$ik" "band No.  KS-energies  QP-energies" "$fn" | tail -1 | awk '{print $1}')
  ln="${ln/:/}"
  
  vbln=$(( ln + vb + 1 ))
  cbln=$(( vbln + 1 ))
  
  #ks_vb=$(awk "FNR == $vbln {print \$2}" "$fn")
  #ks_cb=$(awk "FNR == $cbln {print \$2}" "$fn")
  #qp_vb=$(awk "FNR == $vbln {print \$3}" "$fn")
  #qp_cb=$(awk "FNR == $cbln {print \$3}" "$fn")
  #qp_gap=$(echo "$qp_cb $qp_vb" | awk '{print($1-$2)}')
  
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
  # step 1: PBE SCF for preconvergence
  cp KPOINTS.scf KPOINTS
  cp INCAR.pbe INCAR
  $vaspcmd > out.pbe 2>&1
  backup_results pbe
  # step 2: coarse hf calculation with fixed charge
  cp "$scfchg" CHGCAR
  cp INCAR.coarse INCAR
  $vaspcmd > out.coarse 2>&1
  # raise if charge has changed
  raise_chgcar_change "$scfchg" "CHGCAR"
  backup_results coarse
  # step 3: accurate hf calculation
  cp INCAR.hf INCAR
  $vaspcmd > out.hf 2>&1
  # raise if charge has changed
  raise_chgcar_change "$scfchg" "CHGCAR"
  backup_results hf
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
  if [ ! -f "$vaspxml" ]; then
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
  vaspxml=$1
  gamma=1
  if (( $# == 2 )); then
    gamma=$2
  fi
  kpts=$(xml_kpts "$vaspxml")
  nkpt=$(echo "$kpts" | wc -l)
  lnwei=$(grep -n -m 1 "<varray name=\"weights\" >" "$vaspxml" | tail -1 | awk '{print $1}')
  lnwei="${lnwei/:/}"
  nkall=$(awk "FNR == $(( lnwei+gamma )) {print int(1.0 / \$2 + 0.1)}" "$vaspxml")
  weigh=$(awk "FNR <= $(( lnwei+nkpt ))&& FNR > $lnwei {print int($nkall * \$2 + 0.1)}" "$vaspxml")
  echo "$kpts" > .kpts.tmp; echo "$weigh" > .weigh.tmp; paste .kpts.tmp .weigh.tmp
  rm -f .kpts.tmp .weigh.tmp
}
