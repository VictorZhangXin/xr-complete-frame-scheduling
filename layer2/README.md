# Layer 2: V3.2 XR importance-weighting platform

This folder is the layer-2 code, result tables and documentation for the report
*Importance Gains and Service Costs in XR Complete-Frame Delivery: A Two-Layer
Controlled Study*. Layer 1 (the completion-aware CA-EDF/EDF study) lives in the
repository root under `sim34/`.

## What is here

- `simulate.py` — frame, trace and slotted-channel model; FIFO, EDF, EDF-safe and
  FA(alpha) policies; deterministic infeasibility drop; per-run metrics.
- `ablation_core.py` — identical to `simulate.py` except for an `abandon` switch,
  used for the early-drop ablation (verified by diff, one toggle only).
- `study.py` — configuration checks, independent hand-calculated tests, 64-channel
  exhaustive comparison, legacy regression.
- `analyze_study.py` — independent frame-level rebuild of run metrics, paired t
  intervals, bootstrap, Holm correction, figures.
- `research_loop.py` — calibration on seeds 4000–4019, frozen alpha selection,
  validation on seeds 5000–5029, no-overwrite output.
- `run.py` — finite paired experiments, burst-failure trace, publish-after-audit.
- `tests.py`, `test_loop.py`, `test_revision.py` — regression and integrity tests.
- `results/validation/runs.csv` — 3120 validation runs.
- `results/calibration/runs.csv` — 300 calibration runs.
- `results/analysis/` — effects, admission breakdown, frozen selection, the
  original audit log and the case-study result summary.

## Environment

Python 3.12, `numpy`, `scipy`, `matplotlib` (versions in `requirements-lock.txt`).
A native Linux run was not claimed; the documented fresh-environment rerun was on
Windows 11 with Python 3.12.14.

## Reproduce

```bash
pip install -r requirements.txt
python tests.py            # unit and regression tests
python run.py --suite smoke --output out_smoke   # small end-to-end check
```

The full calibration/validation loop is `python research_loop.py --output <new_dir>`
(roughly 3420 runs; it refuses to overwrite an existing directory).

## Data availability

Per-run CSVs and all analysis scripts are included. The raw per-frame tables
(`frames.csv.gz`, about 34 MB) are kept in the group's local archive and are not
in this repository; they can be provided on request. No traffic was regenerated
and no parameter re-selected after the validation seeds were opened.

## Provenance

Layer-2 platform developed by the group (Ma Yuanfei) and reviewed by the group.
Layer-1 model and code are in `sim34/` at the repository root.
