# -*- coding: utf-8 -*-
"""Regenerate the four paper figures from the archived result tables.

Run from the repository root:

    python paper/build/make_figs.py

Outputs are written to paper/figures/.
"""

import csv
import math
import statistics
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "paper" / "figures"
W, H = 3.35, 2.45

plt.rcParams.update({
    "font.size": 7, "axes.labelsize": 7, "xtick.labelsize": 6.5,
    "ytick.labelsize": 6.5, "legend.fontsize": 5.8, "axes.linewidth": 0.6,
    "xtick.major.width": 0.6, "ytick.major.width": 0.6, "lines.linewidth": 1.1,
    "lines.markersize": 3, "figure.dpi": 300,
})


def ci95(values, n=10):
    m = statistics.mean(values)
    sd = statistics.stdev(values)
    t = 2.262 if n == 10 else 2.045
    return m, t * sd / math.sqrt(n)


def main():
    OUT.mkdir(parents=True, exist_ok=True)

    # ---- Fig. 1: layer 1 ----
    rows = [r for r in csv.DictReader(open(ROOT / "layer1/results/raw_main.csv", encoding="utf-8"))
            if abs(float(r["load"]) - 0.6) < 1e-9 and abs(float(r["loss"]) - 0.01) < 1e-9]
    policies = ["FIFO", "EDF", "CA-EDF", "CA-VD"]
    means, errs = [], []
    for policy in policies:
        m, h = ci95([float(r["cfr"]) for r in rows if r["policy"] == policy])
        means.append(m * 100)
        errs.append(h * 100)
    fig, ax = plt.subplots(figsize=(W, H))
    ax.bar(range(4), means, yerr=errs, capsize=2.5, width=0.62,
           color=["#6b7280", "#1d4ed8", "#ea580c", "#15803d"], edgecolor="white")
    ax.set_xticks(range(4))
    ax.set_xticklabels(policies)
    ax.set_ylabel("On-time complete frames (%)")
    ax.set_ylim(60, 86)
    ax.grid(alpha=0.25, axis="y", linewidth=0.4)
    for i, m in enumerate(means):
        ax.text(i, m + 1.2, f"{m:.1f}", ha="center", fontsize=6)
    fig.tight_layout()
    fig.savefig(OUT / "fig1_layer1.png", bbox_inches="tight", pad_inches=0.02)
    plt.close(fig)

    # ---- Fig. 2: representative layer 2 ----
    val = list(csv.DictReader(open(ROOT / "layer2/results/validation/runs.csv", encoding="utf-8")))
    sc10 = [r for r in val if int(r["scenario"]) == 10]
    policies2 = ["FA0", "FA0.125", "FA1", "EDF_safe"]
    labels = ["FA(0)", "FA(0.125)", "FA(1)", "EDF-safe"]
    weighted, ordinary = [], []
    for p in policies2:
        weighted.append(statistics.mean(float(r["weighted_fraction"]) for r in sc10 if r["policy"] == p) * 100)
        ordinary.append(statistics.mean(float(r["low_completion_fraction"]) for r in sc10 if r["policy"] == p) * 100)
    x = np.arange(len(policies2))
    fig, ax = plt.subplots(figsize=(W, H))
    ax.bar(x - 0.18, weighted, 0.36, label="Weighted", color="#1d4ed8")
    ax.bar(x + 0.18, ordinary, 0.36, label="Ordinary", color="#ea580c")
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=6.3)
    ax.set_ylabel("On-time complete frames (%)")
    ax.set_ylim(60, 96)
    ax.legend(frameon=False, loc="upper left")
    ax.grid(alpha=0.25, axis="y", linewidth=0.4)
    fig.tight_layout()
    fig.savefig(OUT / "fig2_layer2.png", bbox_inches="tight", pad_inches=0.02)
    plt.close(fig)

    # ---- Fig. 3: calibration trade-off ----
    cal = list(csv.DictReader(open(ROOT / "layer2/results/calibration/runs.csv", encoding="utf-8")))
    alphas = [0.125, 0.25, 0.5, 1.0]
    gain, loss = [], []
    for a in alphas:
        g, l = [], []
        for sc in range(3):
            base = {int(r["seed"]): r for r in cal if int(r["scenario"]) == sc and r["policy"] == "FA0"}
            cand = {int(r["seed"]): r for r in cal if int(r["scenario"]) == sc and r["policy"] == f"FA{a:g}"}
            for s in base:
                g.append(float(cand[s]["weighted_fraction"]) - float(base[s]["weighted_fraction"]))
                l.append(float(base[s]["low_completion_fraction"]) - float(cand[s]["low_completion_fraction"]))
        gain.append(statistics.mean(g) * 100)
        loss.append(statistics.mean(l) * 100)
    fig, ax = plt.subplots(figsize=(W, H))
    ax.plot(loss, gain, "-o", color="#1d4ed8")
    ax.text(1.72, 1.02, r"$\alpha$=0.125", fontsize=6)
    ax.text(2.35, 2.12, r"$\alpha$=0.25", fontsize=6)
    ax.text(4.05, 3.95, r"$\alpha$=0.5", fontsize=6)
    ax.text(6.15, 5.02, r"$\alpha$=1", fontsize=6)
    ax.axvline(2.0, color="#b91c1c", linestyle="--", linewidth=0.8)
    ax.text(2.12, max(gain) * 0.92, "2 pp budget", color="#b91c1c", fontsize=5.8)
    ax.set_xlim(1.0, 7.2)
    ax.set_ylim(0.8, max(gain) + 0.5)
    ax.set_xlabel("Ordinary-frame loss (pp)")
    ax.set_ylabel("Weighted gain (pp)")
    ax.grid(alpha=0.25, linewidth=0.4)
    fig.tight_layout()
    fig.savefig(OUT / "fig3_tradeoff.png", bbox_inches="tight", pad_inches=0.02)
    plt.close(fig)

    # ---- Fig. 4: selected vs EDF-safe across 13 configurations ----
    eff = list(csv.DictReader(open(ROOT / "layer2/results/analysis/effects.csv", encoding="utf-8")))
    rows4 = [r for r in eff if r["left"] == "FA0.125" and r["right"] == "EDF_safe"
             and r["metric"] == "weighted_fraction"]
    rows4.sort(key=lambda r: float(r["mean"]))
    names = {0: "40/30", 1: "40/45", 2: "40/60", 3: "80/30", 4: "80/45", 5: "80/60",
             6: "160/30", 7: "160/45", 8: "160/60", 9: "4096/30", 10: "4096/45",
             11: "4096/60", 12: "4096/45 burst"}
    m = [float(r["mean"]) * 100 for r in rows4]
    lo = [float(r["ci_low"]) * 100 for r in rows4]
    hi = [float(r["ci_high"]) * 100 for r in rows4]
    fig, ax = plt.subplots(figsize=(W, 3.1))
    ax.errorbar(m, np.arange(len(rows4)),
                xerr=[np.array(m) - np.array(lo), np.array(hi) - np.array(m)],
                fmt="o", capsize=2, color="#1d4ed8", markersize=3)
    ax.axvline(0, color="black", linewidth=0.7)
    ax.set_yticks(np.arange(len(rows4)))
    ax.set_yticklabels([names[int(r["scenario"])] for r in rows4], fontsize=5.6)
    ax.set_xlabel("Weighted change vs EDF-safe (pp)")
    ax.grid(alpha=0.25, axis="x", linewidth=0.4)
    fig.tight_layout()
    fig.savefig(OUT / "fig4_boundaries.png", bbox_inches="tight", pad_inches=0.02)
    plt.close(fig)
    print("figures written to", OUT)


if __name__ == "__main__":
    main()
