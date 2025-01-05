
2025-1-4

Found a clue on the high variance of xmrig results: turbostat running in the
background at 5 Hz adds ~800 kH/s, even when all it's doing is `--show usec`.

10 hz seems to work *slightly* better than 5 hz, but it's a negligible difference.

Doesnt work if it's not running on E-cores.  Doesn't work if's running on only 1 E-core.
Minimum reproducer seems to be:

    turbostat --quiet --show usec --interval 0.1 --cpu 8-19

Recorded a pair of scheduler traces of xmrig running with (good.trace.dat) and
without (bad.trace.dat) the background turbostat at 20 Hz. The command to do
that is:

    sudo trace-cmd record -e sched -- sleep 0.5

Analyzed as follows:

  1. Open in kernelshark.  
  2. Filter to one cluster of E-cores with Plots -> CPU.  
  3. Filter out `sched_stat_runtime` events by unchecking them in Filter ->
     Events.  
  4. Zoom in on one group of pips.  
  5. Double click the first, to attach marker A to that one and scroll the
     table to the proper timestamp.  
  6. Swtich to marker B, and arrow-key through the table to see what's going on.

Turbostat's behavior is that it wakes on the last E-core at the beginning of
the sampling interval, then migrates rapidly from e-core to e-core in sequence,
starting with the first (8), presumably by setting its affinity, then goes back
to sleep.

To eliminate variables, I implemented `ecore-tickler.py`, found in this same
directory, which rotates its own affinity in a similar fashion, but does
absolutely nothing else.

Initally, it was crashing out due to negative sleep lengths caused by wakeup
latency (really, linux?). Wrapping with `sudo chrt 1` worked as a bandaid fix,
but I fixed it to run without that.

Although, the tickling seems to be *very* slightly more effective with chrt,
just based on eyeballing the hashrate while mining monero.

Effect of tickling


