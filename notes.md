2025-1-4

Found a clue on the high variance of xmrig results: turbostat running in the
background at 5 Hz adds ~800 kH/s, even when all it's doing is `--show usec`.

10 hz seems to work _slightly_ better than 5 hz, but it's a negligible difference.

Doesn't work if it's not running on E-cores. Doesn't work if's running on only 1
E-core. Minimum reproducer seems to be:

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

Although, the tickling seems to be _very_ slightly more effective with chrt,
just based on eyeballing the hashrate while mining monero.

Effect of tickling at 5 hz, perfgov:

`xmrig --bench=1M` on e-cores only, `MSR_PREFETCH_CONTROL = 0xa5`, which is
0x25 + the bit the disables the Array of Pointers prefetcher, which is locked
as of BIOS 2.22.AS05, single run, avg/peak:

- Untickled: 4992 / 6444
- Tickled : 6444 / 6457

Conducted further tests of various tickling parameters, with `xmrig --bench=1M`
on all cores, `MSR_PREFETCH_CONTROL = 0x80`, which is default as of BIOS
2.22.AS05. Detailed results in `test_tickler_params_result.txt`. Summary of 5
runs:

| prio        | timing  | interval | median kH/s | peak kH/s |
| ----------- | ------- | -------- | ----------: | --------: |
| no tickling | n/a     | n/a      |      8813.7 |    8841.6 |
| realtime    | sync    | 0.2      |      9720.3 |    9854.6 |
| realtime    | sync    | 0.1      |      9882.0 |    9954.7 |
| realtime    | sync    | 0.05     |      9810.8 |    9970.5 |
| realtime    | stagger | 0.2      |      9829.4 |    9861.1 |
| realtime    | stagger | 0.1      |      9921.2 |    9999.9 |
| realtime    | stagger | 0.05     |      9894.1 |    9876.2 |
| sched_other | stagger | 0.1      |      9670.1 |    9876.2 |

"Best" appears to be realtime priority stagger at 10 Hz.

Reported to xmrig: https://github.com/xmrig/xmrig/issues/3612

2025-1-6

On suggestion of SChernykh, checked effect of --cpu-no-yield. Or rather, effect
of switching between `{"yield": false}` and `{"yield": true}` in the CPU section
of config.json. Full data added to test_tickler_params_result.txt. Summary:

| yield | tickling      | median kH/s | peak kH/s |
| ----- | ------------- | ----------: | --------: |
| true  | no            |      8632.7 |    8943.3 |
| true  | 10 Hz stagger |      9862.4 |   10013.7 |
| false | no            |      8549.5 |    8704.4 |
| false | 10 Hz stagger |      9910.5 |    9966.4 |

New theory: The clustered L2 cache (4 MiB) is too small to hold 4 threads worth
of scratchpad. If two cores get a "head start", could they force the other two
threads hotter part of working set out to L3, wasting L2 space on less
profitable scratchpad? In that case, the slow threads might be punished even
more for having less memory traffic, in a positive feedback effect. The
equillibrium could then be disrupted by the fast threads getting de-scheduled.
If it snowballs slowly, that might explain the Uncomputerly Long timescale?

Experiments to try:

1. `perf stat` cache hit rate response to tickling.
2. Does tickling still help with only 1 or 2 threads per cluster?
3. Pick out some phoronix tests that are CPU-intensive, parallel, and have
   long-lived threads with little blocking. See if anything else benefits from
   E-core tickling. Maybe y-cruncher?
