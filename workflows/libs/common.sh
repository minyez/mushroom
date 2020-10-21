#!/usr/bin/env bash
# constants and common utilities for workflows
_PI=3.141592653589793
_HA2EV=27.21138602
_AU2ANG=0.52917721067

function ev2ha () {
  echo "$1 $_HA2EV" | awk '{printf("%f\n", $1/$2)}'
}

function ha2ev () {
  echo "$1 $_HA2EV" | awk '{printf("%f\n", $1*$2)}'
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
  #    since determinant of a matrix is equal to that of its tranpose
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
  # $1: ENCUT in eV
  # $2: volume of crystal, in Angstrom^3
  if (( $# != 2 )); then
    exit 1
  fi
  encut=$1
  vol=$2
  echo "$encut $_HA2EV $_AU2ANG $vol $_PI" | awk \
    '{printf("%d\n", 0.5 + (2.0*$1/$2)**1.5 / $3**3 * $4 / 6.0 / $5**2)}'
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
