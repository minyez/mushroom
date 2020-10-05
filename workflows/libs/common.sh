#!/usr/bin/env bash
# common utilities for workflows

function comment_datetime () {
  # create a datetime comment
  echo "# $(date +"%Y-%m-%d %a %H:%M:%S")"
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
  s=$(diff "$file1" "$file2")
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
