"""Experiment driver: paired comparisons across seeds, CSV output, 95% CIs."""

import csv
import os
import statistics
from dataclasses import replace

from .model import Params, simulate
from .policies import POLICIES

# two-sided 95% t quantiles (small samples)
T95 = {5: 2.776, 10: 2.262, 15: 2.145, 20: 2.093, 30: 2.042}

FIELDS = ["policy", "seed", "load", "loss", "theta", "scale", "pkt_min",
          "pkt_max", "frames", "cfr", "iw_cfr", "waste", "lat_mean",
          "lat_p95", "abandoned", "expired", "unfinished", "done",
          "attempts", "cfr_a", "cfr_b"]


def ci95(values):
    n = len(values)
    if n < 2:
        return 0.0
    sd = statistics.stdev(values)
    t = T95.get(n, 1.96)
    return t * sd / (n ** 0.5)


def run_config(params: Params, policies=None):
    """Run every policy on the *same* channel realisation (paired)."""
    policies = policies or list(POLICIES)
    rows = []
    for name in policies:
        res = simulate(params, POLICIES[name])
        res.update(policy=name, seed=params.seed, load=params.bg_load,
                   loss=params.p_loss, theta=params.theta)
        rows.append(res)
    return rows


def sweep(base: Params, loads, losses, seeds, out_csv):
    rows = []
    for load in loads:
        for loss in losses:
            for seed in seeds:
                rows.extend(run_config(replace(base, bg_load=load,
                                               p_loss=loss, seed=seed)))
    _write(rows, out_csv)
    return rows


def sweep_frame_size(base: Params, sizes, seeds, out_csv):
    rows = []
    for lo, hi in sizes:
        for seed in seeds:
            rs = run_config(replace(base, pkt_min=lo, pkt_max=hi, seed=seed))
            for r in rs:
                r["pkt_min"], r["pkt_max"] = lo, hi
            rows.extend(rs)
    _write(rows, out_csv)
    return rows


def sweep_deadline(base: Params, scales, seeds, out_csv):
    """scale = deadline / frame interval (1.0 is the stress case)."""
    rows = []
    for s in scales:
        for seed in seeds:
            rs = run_config(replace(base,
                                    d_a=max(2, int(round(base.tf_a * s))),
                                    d_b=max(2, int(round(base.tf_b * s))),
                                    seed=seed))
            for r in rs:
                r["scale"] = s
            rows.extend(rs)
    _write(rows, out_csv)
    return rows


def summarise(rows, keys=("policy", "load", "loss")):
    groups = {}
    for r in rows:
        k = tuple(r[x] for x in keys)
        groups.setdefault(k, []).append(r)
    out = []
    for k, rs in sorted(groups.items(), key=lambda kv: tuple(map(str, kv[0]))):
        item = dict(zip(keys, k))
        for metric in ("cfr", "iw_cfr", "waste", "lat_mean", "abandoned"):
            vals = [r[metric] for r in rs]
            item[metric] = statistics.mean(vals)
            item[metric + "_ci"] = ci95(vals)
        item["n"] = len(rs)
        out.append(item)
    return out


def _write(rows, path):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def write_summary(summary, path):
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(summary[0].keys()))
        w.writeheader()
        w.writerows(summary)
