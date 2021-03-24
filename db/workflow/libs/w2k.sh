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
