#!/usr/bin/env python3

import argparse
import os
import time
import typing
from pathlib import Path


class RegularClock:
    """Equal-interval loop timer"""

    def __init__(self, interval: float):
        self.interval = interval
        self.tot_err: float = 0
        self.t_next = time.time()

    def wait(self) -> None:
        self.t_next += self.interval
        now = time.time()
        if now < self.t_next:
            time.sleep(self.t_next - now)
        else:
            self.tot_err += now - self.t_next
            self.t_next = now


def tickle_burst(cores: list[int], clock: RegularClock) -> typing.Never:
    while True:
        for cpu_num in cores:
            os.sched_setaffinity(0, (cpu_num,))  # 0: self
        clock.wait()


def tickle_stagger(cores: list[int], clock: RegularClock) -> typing.Never:
    while True:
        for cpu_num in cores:
            os.sched_setaffinity(0, (cpu_num,))  # 0: self
            clock.wait()


def list_e_cores() -> list[int]:
    # An e-core is considered to be a core that is part of a cluster
    return [
        cpu
        for cpu in os.sched_getaffinity(0)
        if "-"
        in Path(
            f"/sys/devices/system/cpu/cpu{cpu}/topology/cluster_cpus_list"
        ).read_text()
    ]


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--interval",
        "-i",
        type=float,
        required=True,
        help="time between full traversals of the E-cores",
    )
    parser.add_argument("--timing", choices=["sync", "stagger"], required=True)
    parser.add_argument("cores", type=int, nargs="*")
    args = parser.parse_args()
    cores = args.cores
    if len(cores) == 0:
        cores = list_e_cores()
        if len(cores) == 0:
            print("No E-cores to tickle; exiting.")
            exit()
        else:
            print(f"Tickling E-cores: {cores}")
    match args.timing:
        case "sync":
            clock = RegularClock(args.interval)
            tickle = tickle_burst
        case "stagger":
            clock = RegularClock(args.interval / len(cores))
            tickle = tickle_stagger
        case _:
            typing.assert_never(args.timing)
    start_time = time.time()
    try:
        tickle(cores, clock)
    except KeyboardInterrupt:
        pass
    finally:
        sleep_err_rel = clock.tot_err / (time.time() - start_time)
        print(
            f"Sleep Err abs: {clock.tot_err:12.6f}    rel: {(sleep_err_rel*100):5.2f}%"
        )
