#!/usr/bin/env bash
# common functions to be used in vasp workflows

function backup_results () {
  # back up OUTCAR EIGENVAL DOSCAR and vasprun.xml
  files=(OUTCAR EIGENVAL DOSCAR vasprun.xml)
  for f in "${files[@]}"; do
    if [ -f "$f" ]; then
      cp "$f" "$f.$1"
    fi
  done
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

function get_nelect () {
  # get the number of electrons (float)
  # $1: outcar file (OUTCAR)
  if (( $# == 0 )); then
    fn="OUTCAR"
  else
    fn=$1
  fi
  awk '/NELECT/ {print $3}' "$fn"
}

function get_vb () {
  # get the number of valence bands
  # $1: outcar file (OUTCAR)
  if (( $# == 0 )); then
    fn="OUTCAR"
  else
    fn=$1
  fi
  awk '/NELECT/ {printf("%d", $3/2.0)}' "$fn"
}

function get_nbands () {
  # get the total number of bands
  # $1: outcar file (OUTCAR)
  if (( $# == 0 )); then
    fn="OUTCAR"
  else
    fn=$1
  fi
  awk '/NBANDS/ {print $15}' "$fn"
}

function get_eigen_ik () {
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

function get_qpc_vb_cb () {
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

function get_encut () {
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
