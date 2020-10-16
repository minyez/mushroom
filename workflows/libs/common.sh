#!/usr/bin/env bash
# common utilities for workflows

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
