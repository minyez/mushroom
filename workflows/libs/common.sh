#!/usr/bin/env bash
# common utilities for workflows

comment_datetime () {
  # create a datetime comment
  echo "# $(date +"%Y-%m-%d %a %H:%M:%S")"
}
