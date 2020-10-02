#!/usr/bin/env bash
# common utilities for workflows

function comment_datetime () {
  # create a datetime comment
  echo "# $(date +"%Y-%m-%d %a %H:%M:%S")"
}
