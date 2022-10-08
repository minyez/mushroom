#!/usr/bin/env bash
# constants and common utilities for workflows
_PI=3.141592653589793
_HA2EV=27.21138602
_AU2ANG=0.52917721067

# TODO precision as argument?
function ev2ha () {
  echo "$1 $_HA2EV" | awk '{printf("%.10f\n", $1/$2)}'
}

function ev2ry () {
  echo "$1 $_HA2EV" | awk '{printf("%.10f\n", $1/$2*2.0)}'
}

function ha2ev () {
  echo "$1 $_HA2EV" | awk '{printf("%.10f\n", $1*$2)}'
}

function ry2ev () {
  echo "$1 $_HA2EV" | awk '{printf("%.10f\n", $1*$2/2.0)}'
}

function comment_datetime () {
  # create a datetime comment
  echo "# $(date +"%Y-%m-%d %a %H:%M:%S")"
}

function raise_noexec () {
  # check if the parsed path/command exists and is executable
  # $1: command or path
  executable=$1
  if which "$executable" &> /dev/null; then
    return 0
  fi
  if [[ -x "$executable" ]]; then
    return 0
  fi
  echo "Valid executable $executable not found"
  exit 1
}

function raise_isdir () {
  # check if directory exists and raise if it does
  # $1: name of directory
  d=$1
  if [ -d "$d" ]; then
    echo "Working directory \"$d\" is found. Delete it first"
    exit 1
  fi
}

function raise_different () {
  # raise if two files are different
  # $1 $2: paths of files
  file1=$1
  file2=$2
  if [ ! -f "$file1" ]; then
    echo "$file1 is not a file"
    exit 1
  fi
  if [ ! -f "$file2" ]; then
    echo "$file2 is not a file"
    exit 1
  fi
  s=$(diff -q "$file1" "$file2")
  if [[ -n "$s" ]]; then
    exit 1
  fi
}

function raise_missing_prereq (){
  # raise when any of pre-requisite files is missing
  # $@: names of pre-requisite files
  for f in "$@"; do
    if [ ! -f "$f" ]; then
      echo "Missing required file \"$f\""
      exit 1
    fi
  done
}

function raise_missing_dir (){
  # raise when any of pre-requisite directories is missing
  # $@: names of pre-requisite directories
  for f in "$@"; do
    if [ ! -d "$f" ]; then
      echo "Missing required directory \"$f\""
      exit 1
    fi
  done
}

function match_directory () {
  echo "$@"
}

function split_str () {
  local -n arr=$1
  if [[ $# == 3 ]]; then
    delim=$3
  else
    delim=" "
  fi
  s="$2$delim"
  while [[ $s ]]; do
      arr+=("${s%%"$delim"*}")
      s=${s#*"$delim"}
  done
}

function triple_prod () {
  # triple product of an array. two kinds of inputs
  # 1. 9 arguments can be either C-like or F-like
  #    since determinant of a matrix is equal to that of its transpose
  # 2. one string composed of 9 floats separated by single space
  if (( $# == 9 )); then
    echo "$@" | awk '{printf("%f\n",$1*($5*$9-$6*$8)-$2*($4*$9-$6*$7)+$3*($4*$8-$5*$7))}'
  elif (( $# == 1 )); then
    arr=()
    s="$1 "
    while [[ $s ]]; do
      arr+=("${s%%" "*}")
      s=${s#*" "}
    done
    echo "${arr[@]}" | awk '{printf("%f\n",$1*($5*$9-$6*$8)-$2*($4*$9-$6*$7)+$3*($4*$8-$5*$7))}'
  else
    exit 1
  fi
}

function estimate_npw () {
  # estimate the maximum number of plane waves
  # $1: ENCUT
  # $2: volume of crystal
  # $3: unit,    "au": ENCUT in Ha, volume in Bohr
  #              "ry": ENCUT in Ry, volume in Bohr
  #         otherwise: ENCUT in eV, volume in Angstrom^3
  case $# in
    0|1 ) echo "Error! must encut and volume"; exit 1;;
    2 ) encut="$1"; vol="$2"; unit="evang" ;;
    * ) encut="$1"; vol="$2"; unit="$3" ;;
  esac
  if [[ "$unit" == "au" ]]; then
    echo "$encut $vol $_PI" | awk \
      '{printf("%d\n", 0.5 + (2.0*$1)**1.5 * $2 / 6.0 / $3**2)}'
  elif [[ "$unit" == "ry" ]]; then
    echo "$encut $vol $_PI" | awk \
      '{printf("%d\n", 0.5 + ($1)**1.5 * $2 / 6.0 / $3**2)}'
  else
    echo "$encut $_HA2EV $_AU2ANG $vol $_PI" | awk \
      '{printf("%d\n", 0.5 + (2.0*$1/$2)**1.5 / $3**3 * $4 / 6.0 / $5**2)}'
  fi
}

function largest_div_below_sqrt () {
  # get the largest divider of integer n below its square root
  num=$1
  sqr=$(echo "$num" | awk '{printf("%d", sqrt($1))}')
  for i in $(seq "$sqr" -1 1); do
    if (( num%i == 0 )); then
      echo "$i"
      break
    fi
  done
}

function confirm () {
  # ask for confirmation
  # $1: default value, 1 for Yes, otherwise No
  # $2: help message
  de="$1"
  if (( de == 1 )); then
    msg="$2? [Y/n]"
  else
    de=0
    msg="$2? [y/N]"
  fi
  echo -n "$msg "
  read -r answer
  if [[ "$answer" == "y" ]] || [[ "$answer" == "Y" ]]; then
    echo 1
  elif [[ "$answer" == "n" ]] || [[ "$answer" == "N" ]]; then
    echo 0
  else
    echo "$de"
  fi
}

function is_a_bigger_than_b () {
  # $1: a
  # $2: b
  case $# in
    2 ) a="$1"; b="$2";;
    * ) echo "$0 need two arguments"; exit 1;;
  esac
  if awk "BEGIN {exit !($a > $b)}"; then
    return 0
  else
    return 1
  fi

}
