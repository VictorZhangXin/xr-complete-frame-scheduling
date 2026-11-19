# sim34 — XR frame-completion scheduling simulator

Topic 34 · EEEN3008J · 2026/27

A small, dependency-free (except plotting) discrete-time simulator that compares
four downlink scheduling rules for XR traffic, where a frame is useful only if
**all** of its packets arrive before the display deadline.

---

## 1. Model in one paragraph

Time is slotted (1 slot = 1 ms). Each slot offers `pkts_per_slot = 2`
transmission opportunities. Background traffic blocks a slot with probability
`ρ`; each transmission fails with probability `p` and the packet must be
retried. Frames arrive from two XR streams (60 fps and 90 fps, hence different
deadlines), are cut into 4–8 packets, and expire at their display deadline.
A frame counts as delivered only when its last packet succeeds in time.

All randomness (slot blocking, per-opportunity success, frame sizes, importance)
is **pre-generated per seed and shared by every policy**, so policies are
compared on exactly the same channel and traffic realisation.

## 2. Parameters (all illustrative unless stated)

| Symbol | Meaning | Value |
|---|---|---|
| `duration_ms` | simulated trace length | 15 000 ms |
| `pkts_per_slot` | opportunities per ms | 2 |
| `tf_a`, `d_a` | stream A interval / deadline | 16 ms / 24 ms (≈60 fps) |
| `tf_b`, `d_b` | stream B interval / deadline | 11 ms / 16 ms (≈90 fps) |
| `pkt_min`, `pkt_max` | packets per frame | 4–8 |
| `p` | per-transmission error rate | 0, 1 %, 5 % |
| `ρ` | background load (slot occupancy) | 0, 0.3, 0.5, 0.6 |
| `p_important`, `w` | importance | 15 % of frames have weight 3, rest 1 |
| `θ` | abandonment threshold | 0.05 |

The 60/90 fps values follow the XR frame rates discussed in 3GPP TR 38.838; the
rest are illustrative and are declared as such in the report.

## 3. Policies

| Name | Rule |
|---|---|
| **FIFO** | oldest frame first, no deadline logic |
| **EDF** | earliest deadline first, never gives up early |
| **CA-EDF** (proposed) | drop a frame when `P(complete in time) < θ`, then EDF |
| **CA-VD** (variant) | same abandonment, then order by `weight / packets_left` |

`P(complete in time)` is a normal approximation of
`P(Binomial(n·c, r) ≥ pending)`, with `n` slots left, `c` opportunities per
slot and `r = (1−ρ)(1−p)` the per-opportunity success probability.

## 4. Run

```bash
python -m sim34.validate          # sanity checks (must all PASS)
python -m sim34.run_experiments   # full sweep, writes results/*.csv (~1 min)
python -m sim34.figures           # needs matplotlib -> results/fig*.png|pdf
```

Quick smoke test: `python -m sim34.run_experiments --quick`.

## 5. Outputs

| File | Content |
|---|---|
| `results/raw_main.csv` | one row per (policy, load, loss, seed) |
| `results/summary_main.csv` | means and 95 % CIs over seeds |
| `results/raw_framesize.csv`, `summary_framesize.csv` | frame-size sweep |
| `results/raw_deadline.csv`, `summary_deadline.csv` | deadline-stress sweep |
| `results/fig1_cfr_vs_load.*` | CFR vs load at p = 1 % |
| `results/fig2_iwcfr_waste.*` | importance-weighted CFR and wasted airtime |
| `results/fig3_size_deadline.*` | frame-size effect and tight-deadline stress |

Main metrics: `cfr` (on-time complete frames / all generated frames),
`iw_cfr` (importance-weighted), `waste` (share of transmission opportunities
spent on frames that never completed).

## 6. Checks implemented (`sim34.validate`)

1. no loss + no background load → CFR = 1.0 and waste = 0 for every policy;
2. frame conservation: generated = completed + expired + abandoned + unfinished;
3. the channel is deterministic per seed (paired comparison);
4. a run is reproducible;
5. `p_complete` decreases as the deadline approaches;
6. a single-packet frame is delivered in its first slot.

## 7. Known limitations (state these in the report)

- Background traffic is a Bernoulli slot occupancy, not a queue with its own
  arrivals and backlogs.
- One packet per opportunity; no coding, no adaptive modulation, no HARQ
  combining (a failed packet is simply retried).
- Frames are independent; dependencies between I/P frames are not modelled.
- `p` and `ρ` are assumed known to the scheduler when computing feasibility
  (a measured long-run estimate, not future knowledge).
- Single cell, single user per stream, no uplink or acknowledgement delay.
- Results are a model-level comparison, not a validation of a commercial system.

## 8. Mapping to the report

| Report section | Uses |
|---|---|
| §II Background | model description, parameter table |
| §VI Method | policies, `p_complete`, θ |
| §VII Results | `summary_*.csv`, Fig. 1–3 |
| §VIII Limitations | section 7 above |
