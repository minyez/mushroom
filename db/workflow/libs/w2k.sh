#!/usr/bin/env bash
# wien2k facilities
function get_casename () {
  if (ls ./*.struct 1> /dev/null 2>&1) ; then
    # get the first matched
    struct=$(find . -maxdepth 1 -regex ".*.struct" -print -quit)
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
      for _ in $(seq 1 $((nprocs-res))); do
        echo "$kperp:$hnm"
      done
    fi
    for _ in $(seq 1 "$res"); do
      echo "$((kperp+1)):$hnm"
    done
  else
    for _ in $(seq 1 "$nprocs"); do
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

function xkgen_noshift () {
  # kgen in an non-interactive mode, always without shift of origin
  # this is done by always adding a 0 when parsing to x kgen
  # $1: x executable
  case $# in
    0 | 1) echo "Need kpoints arguments"; exit 1;;
    2) x=$1; nkpts=$2; nx=; ny=; nz=;;
    4) x=$1; nkpts=; nx=$2; ny=$3; nz=$4;;
    *) echo "Invalid kpoints arguments, either 1 (nkpts) or 3 (nx ny nz)"; exit 1;;
  esac
  if [[ -n "$nkpts" ]]; then
    echo "$nkpts" | $x kgen
  else
    printf "0\n%d %d %d\n0\n" "$nx" "$ny" "$nz" | $x kgen
  fi
}

function savelapw() {
  # TODO
  # save run_lapw results
  # Although save_lapw is available for use, some files are not included by default,
  # e.g. scf
  # $1: directory to save to
  rm -f ./*.broyd*
}

