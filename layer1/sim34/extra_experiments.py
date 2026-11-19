"""Additional control experiments: abandonment threshold and deadline homogeneity."""

import csv
import os
import statistics
from dataclasses import replace

from .experiments import ci95, run_config, write_summary
from .model import Params

OUT = "results"


def theta_sweep(base: Params, thetas, seeds, path):
    rows = []
    for theta in thetas:
        for seed in seeds:
            rs = run_config(replace(base, theta=theta, seed=seed),
                            policies=["CA-EDF", "CA-VD"])
            for r in rs:
                r["theta"] = theta
            rows.extend(rs)
    _write(rows, path, ["policy", "theta", "seed", "cfr", "iw_cfr", "waste", "abandoned"])
    return rows


def deadline_control(base: Params, same_deadline: bool, seeds, path):
    rows = []
    for seed in seeds:
        p = replace(base, d_b=base.d_a, seed=seed) if same_deadline else replace(base, seed=seed)
        rs = run_config(p)
        for r in rs:
            r["deadline_case"] = "equal" if same_deadline else "split"
        rows.extend(rs)
    _write(rows, path, ["policy", "deadline_case", "seed", "cfr", "iw_cfr", "waste"])
    return rows


def _write(rows, path, fields):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def summarise(rows, keys):
    groups = {}
    for r in rows:
        groups.setdefault(tuple(r[k] for k in keys), []).append(r)
    out = []
    for k, rs in sorted(groups.items(), key=lambda kv: tuple(map(str, kv[0]))):
        item = dict(zip(keys, k))
        for m in ("cfr", "iw_cfr", "waste"):
            vals = [r[m] for r in rs]
            item[m] = statistics.mean(vals)
            item[m + "_ci"] = ci95(vals)
        out.append(item)
    return out


def main(seeds=range(10)):
    base = Params(duration_ms=15000, bg_load=0.6, p_loss=0.01)
    rows = theta_sweep(base, [0.01, 0.05, 0.20], seeds, f"{OUT}/raw_theta.csv")
    write_summary(summarise(rows, ("policy", "theta")), f"{OUT}/summary_theta.csv")

    rows2 = deadline_control(base, False, seeds, f"{OUT}/raw_deadline_split.csv")
    rows2 += deadline_control(base, True, seeds, f"{OUT}/raw_deadline_equal.csv")
    write_summary(summarise(rows2, ("policy", "deadline_case")),
                  f"{OUT}/summary_deadline_equal.csv")
    print("extra experiments written")


if __name__ == "__main__":
    main()
