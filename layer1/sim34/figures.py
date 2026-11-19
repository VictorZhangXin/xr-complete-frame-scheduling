"""
Make the report figures at final print size (single column, ~8.2 cm wide).

Run from the workspace root (needs matplotlib):
    python -m sim34.figures
"""

import csv
import os
import sys

sys.path.insert(0, os.path.abspath(".deps_mpl"))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

OUT = "results"
POLICIES = ["FIFO", "EDF", "CA-EDF", "CA-VD"]
STYLE = {
    "FIFO":   dict(color="#6b7280", marker="o", ls="--"),
    "EDF":    dict(color="#1d4ed8", marker="s", ls="-"),
    "CA-EDF": dict(color="#ea580c", marker="^", ls="-"),
    "CA-VD":  dict(color="#15803d", marker="D", ls="-"),
}
W, H = 3.35, 2.45          # inches -> ~8.5 cm at 1:1 print scale

plt.rcParams.update({
    "font.size": 7,
    "axes.labelsize": 7,
    "axes.titlesize": 7,
    "xtick.labelsize": 6.5,
    "ytick.labelsize": 6.5,
    "legend.fontsize": 6,
    "axes.linewidth": 0.6,
    "xtick.major.width": 0.6,
    "ytick.major.width": 0.6,
    "lines.linewidth": 1.2,
    "lines.markersize": 3.2,
    "figure.dpi": 300,
})


def load(name):
    with open(os.path.join(OUT, name), encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def series(rows, policy, key, xkey):
    pts = [r for r in rows if r["policy"] == policy]
    pts.sort(key=lambda r: float(r[xkey]))
    return ([float(r[xkey]) for r in pts],
            [float(r[key]) for r in pts],
            [float(r[key + "_ci"]) for r in pts])


def save(fig, name):
    fig.savefig(f"{OUT}/{name}.png", bbox_inches="tight", pad_inches=0.02)
    fig.savefig(f"{OUT}/{name}.pdf", bbox_inches="tight", pad_inches=0.02)
    plt.close(fig)


def line_plot(rows, key, xkey, xlabel, ylabel, name, ylim=None, xticks=None,
              legend_loc="lower left"):
    fig, ax = plt.subplots(figsize=(W, H))
    for p in POLICIES:
        x, y, e = series(rows, p, key, xkey)
        ax.errorbar(x, y, yerr=e, capsize=2, label=p, **STYLE[p])
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    if ylim:
        ax.set_ylim(*ylim)
    if xticks:
        ax.set_xticks(xticks)
    ax.grid(alpha=0.25, linewidth=0.4)
    ax.legend(loc=legend_loc, frameon=False, handlelength=1.8)
    fig.tight_layout()
    save(fig, name)


def fig_load(rows):
    line_plot(rows, "cfr", "load", "Background load $\\rho$",
              "Complete-frame ratio", "fig1_cfr_vs_load",
              ylim=(0.55, 1.03), xticks=[0.0, 0.3, 0.5, 0.6])


def fig_iw(rows):
    line_plot(rows, "iw_cfr", "load", "Background load $\\rho$",
              "Importance-weighted CFR", "fig2_iwcfr",
              ylim=(0.55, 1.03), xticks=[0.0, 0.3, 0.5, 0.6])


def fig_waste(rows):
    line_plot(rows, "waste", "load", "Background load $\\rho$",
              "Wasted airtime", "fig3_waste",
              ylim=(0.0, 0.25), xticks=[0.0, 0.3, 0.5, 0.6], legend_loc="upper left")


def fig_size(rows):
    fig, ax = plt.subplots(figsize=(W, H))
    for p in POLICIES:
        pts = [r for r in rows if r["policy"] == p]
        pts.sort(key=lambda r: int(r["pkt_min"]))
        x = [(int(r["pkt_min"]) + int(r["pkt_max"])) / 2 for r in pts]
        y = [float(r["cfr"]) for r in pts]
        ax.plot(x, y, label=p, **STYLE[p])
    ax.set_xlabel("Mean packets per frame")
    ax.set_ylabel("Complete-frame ratio")
    ax.set_xticks([5, 7, 9])
    ax.grid(alpha=0.25, linewidth=0.4)
    ax.legend(frameon=False, handlelength=1.8)
    fig.tight_layout()
    save(fig, "fig4_frame_size")


def fig_deadline(rows):
    fig, ax = plt.subplots(figsize=(W, H))
    for p in POLICIES:
        pts = [r for r in rows if r["policy"] == p]
        pts.sort(key=lambda r: float(r["scale"]))
        x = [float(r["scale"]) for r in pts]
        y = [float(r["cfr"]) for r in pts]
        ax.plot(x, y, label=p, **STYLE[p])
    ax.set_xlabel("Deadline / frame interval")
    ax.set_ylabel("Complete-frame ratio")
    ax.set_xticks([1.0, 1.5, 2.0])
    ax.grid(alpha=0.25, linewidth=0.4)
    ax.legend(frameon=False, handlelength=1.8, loc="lower right")
    fig.tight_layout()
    save(fig, "fig5_deadline_stress")


def fig_theta(rows):
    fig, ax = plt.subplots(figsize=(W, H))
    for p in ("CA-EDF", "CA-VD"):
        pts = [r for r in rows if r["policy"] == p]
        pts.sort(key=lambda r: float(r["theta"]))
        x = [float(r["theta"]) for r in pts]
        y = [float(r["cfr"]) for r in pts]
        e = [float(r["cfr_ci"]) for r in pts]
        ax.errorbar(x, y, yerr=e, capsize=2, label=p, **STYLE[p])
    ax.set_xlabel("Abandonment threshold $\\theta$")
    ax.set_ylabel("Complete-frame ratio")
    ax.set_xscale("log")
    ax.set_xticks([0.01, 0.05, 0.20])
    ax.set_xticklabels(["0.01", "0.05", "0.20"])
    ax.grid(alpha=0.25, linewidth=0.4)
    ax.legend(frameon=False, handlelength=1.8)
    fig.tight_layout()
    save(fig, "fig6_theta")


def fig_deadline_control(rows):
    fig, ax = plt.subplots(figsize=(W, H))
    labels = POLICIES
    width = 0.36
    for k, case in enumerate(("split", "equal")):
        vals = []
        for p in labels:
            pts = [r for r in rows if r["policy"] == p and r["deadline_case"] == case]
            vals.append(float(pts[0]["cfr"]) if pts else 0.0)
        xs = [i + (k - 0.5) * width for i in range(len(labels))]
        ax.bar(xs, vals, width=width,
               label=("split deadlines" if case == "split" else "equal deadlines"),
               color=("#ea580c" if case == "split" else "#9ca3af"),
               edgecolor="white", linewidth=0.6)
    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(labels, fontsize=6.5)
    ax.set_ylabel("Complete-frame ratio")
    ax.set_ylim(0.6, 0.9)
    ax.grid(alpha=0.25, axis="y", linewidth=0.4)
    ax.legend(frameon=False, fontsize=5.8, loc="lower right")
    fig.tight_layout()
    save(fig, "fig7_deadline_control")


def main():
    main_rows = [r for r in load("summary_main.csv")
                 if abs(float(r["loss"]) - 0.01) < 1e-9]
    fig_load(main_rows)
    fig_iw(main_rows)
    fig_waste(main_rows)
    fig_size(load("summary_framesize.csv"))
    fig_deadline(load("summary_deadline.csv"))
    fig_theta(load("summary_theta.csv"))
    fig_deadline_control(load("summary_deadline_equal.csv"))
    print("figures:", ", ".join(sorted(f for f in os.listdir(OUT)
                                        if f.startswith("fig") and f.endswith(".png"))))


if __name__ == "__main__":
    main()
