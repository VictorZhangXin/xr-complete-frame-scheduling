"""
Run the full experiment set for Topic 34 and write CSV results.

Usage (from the workspace root):
    python -m sim34.run_experiments            # full sweep (~1-2 min)
    python -m sim34.run_experiments --quick    # 3 seeds, shorter trace
"""

import os
import sys
from dataclasses import replace

from .experiments import (sweep, sweep_deadline, sweep_frame_size,
                          summarise, write_summary)
from .model import Params

OUT = "results"


def main(quick=False):
    os.makedirs(OUT, exist_ok=True)
    base = Params(duration_ms=6000 if quick else 15000)
    seeds = range(3 if quick else 10)

    print("1/3  main sweep: load x loss ...")
    rows = sweep(base, [0.0, 0.3, 0.5, 0.6], [0.0, 0.01, 0.05], seeds,
                 f"{OUT}/raw_main.csv")
    write_summary(summarise(rows), f"{OUT}/summary_main.csv")

    print("2/3  frame-size sweep ...")
    rows2 = sweep_frame_size(replace(base, bg_load=0.6, p_loss=0.01),
                             [(4, 6), (6, 8), (8, 10)], seeds,
                             f"{OUT}/raw_framesize.csv")
    write_summary(summarise(rows2, keys=("policy", "pkt_min", "pkt_max")),
                  f"{OUT}/summary_framesize.csv")

    print("3/3  deadline stress sweep ...")
    rows3 = sweep_deadline(replace(base, bg_load=0.6, p_loss=0.05),
                           [1.0, 1.5, 2.0], seeds, f"{OUT}/raw_deadline.csv")
    write_summary(summarise(rows3, keys=("policy", "scale")),
                  f"{OUT}/summary_deadline.csv")

    print(f"done -> {os.path.abspath(OUT)}")
    return rows, rows2, rows3


if __name__ == "__main__":
    main(quick="--quick" in sys.argv)
