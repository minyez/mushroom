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
