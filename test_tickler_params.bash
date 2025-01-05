#!/usr/bin/env bash

set -eu

rootdir="$(git rev-parse --path-format=relative --show-toplevel)"

xmrig () {
    echo -n "" >/tmp/monero-bench-results.txt # clear
    for i in {1..5}; do
        echo "$i / 5 ..."
        "$rootdir/tools/benchmarks/xmrig-1M.bash" >> /tmp/monero-bench-results.txt
    done
    sort -nk4,4 /tmp/monero-bench-results.txt
}

test_with_background_command () {
    echo ""
    echo "background: $*"
    "$@" &
    bg_pid=$!
    sleep 0.1
    xmrig
    kill $bg_pid
    wait
}

sudo cpupower frequency-set -g performance
sudo cpupower set --perf-bias 0

test_with_background_command sleep infinity

test_with_background_command sudo chrt 1 ./ecore-tickler.py --timing sync --interval 0.2
test_with_background_command sudo chrt 1 ./ecore-tickler.py --timing sync --interval 0.1
test_with_background_command sudo chrt 1 ./ecore-tickler.py --timing sync --interval 0.05

test_with_background_command sudo chrt 1 ./ecore-tickler.py --timing stagger --interval 0.2
test_with_background_command sudo chrt 1 ./ecore-tickler.py --timing stagger --interval 0.1
test_with_background_command sudo chrt 1 ./ecore-tickler.py --timing stagger --interval 0.05

test_with_background_command ./ecore-tickler.py --timing stagger --interval 0.1
