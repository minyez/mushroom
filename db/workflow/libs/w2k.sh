#!/usr/bin/env bash
# wien2k facilities
function get_casename () {
  if (ls ./*.struct 1> /dev/null 2>&1) ; then
    # get the first matched
    struct=$(find . -maxdepth 0 -regex ".*.struct" -print -quit)
  else
    return 1
  fi
  casename=$(basename "$struct")
  echo "${casename%.struct}"
}

function gen_machinefile () {
  # $1: #of processors
  # $2: #of kpoints
  case $# in
    0 | 1) echo "Need number of processors & kpoints"; exit 1;;
    *) nprocs=$1; nkpts=$2;;
  esac
  hnm=$(hostname)
  res=$((nkpts%nprocs))
  kperp=$(echo "$nprocs $nkpts $res" | awk '{print(($2-$3)/$1)}')
  if (( res > 0 )); then
    if (( kperp > 0 )); then
      for i in $(seq 1 $((nprocs-res))); do
        echo "$kperp:$hnm"
      done
    fi
    for i in $(seq 1 "$res"); do
      echo "$((kperp+1)):$hnm"
    done
  else
    for i in $(seq 1 "$nprocs"); do
      echo "$kperp:$hnm"
    done
  fi
  echo ""
  echo "granularity:1"
  echo "extrafine:1"
}

function clean_machinefile() {
  # cleanup all machine files generated autmatically by wien2k
  # excluding .machines
  rm -f .machine[^s]*
}
