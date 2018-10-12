#!/bin/sh

basedir="$1"
testset="$2"

export PATH=$(pwd):$PATH

shuf() { awk 'BEGIN {srand(); OFMT="%.17f"} {print rand(), $0}' "$@" |
               sort -k1,1n | cut -d ' ' -f2-; }

tasks_files=$(echo $(for f in $(ls ${basedir}tasks/${testset}/*/task.json | shuf); do printf "$f,"; done) | sed -e s/,\$//g)
echo
echo "Running through tests:"
echo "---"
echo "$tasks_files"
echo
create_task.py --tasks_file $tasks_files --runtests

