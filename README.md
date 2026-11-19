# XR Complete-Frame Scheduling — Two-Layer Study

Code, data and paper for *Importance Gains and Service Costs in XR Complete-Frame
Delivery: A Two-Layer Controlled Study* (EEEN3008J Wireless Communications, group
project 2026/27, Topic 34).

The paper studies XR frames that are segmented into several packets: a frame is
usable only when every necessary packet arrives before its display deadline. It
combines two controlled discrete-event studies.

## Structure

```
layer1/            completion-aware scheduling (EDF vs CA-EDF, two streams)
  sim34/           simulator, policies, experiments, validation
  results/         per-run CSVs behind the layer-1 table and figure
layer2/            importance-weighted scheduling (FA(alpha), EDF-safe, V3.2)
  simulate.py      frame/trace/channel model and policies
  study.py         checks, hand tests, exhaustive small-channel comparison
  analyze_study.py metrics, paired intervals, bootstrap, Holm
  research_loop.py calibration on seeds 4000-4019, frozen alpha, validation 5000-5029
  run.py           finite paired experiments with burst-failure trace
  results/         3120 validation runs, 300 calibration runs, effects, admission
paper/
  XR_TwoLayer_EN.pdf / .docx   final paper
  figures/                     print-size figures used in the paper
  build/                       content sources and build script for the DOCX
```

## Reproduce

Layer 1 (standard library plus matplotlib for the figures):

```bash
cd layer1
pip install -r requirements.txt            # matplotlib
python -m sim34.validate                   # six consistency checks
python -m sim34.run_experiments            # regenerates results/raw_*.csv
python -m sim34.figures                    # optional; needs matplotlib
```

Layer 2:

```bash
cd layer2
pip install -r requirements.txt            # numpy, scipy, matplotlib
python tests.py                            # unit, oracle and legacy regression tests
python research_loop.py --output out       # 3420 runs; refuses to overwrite
```

The archived `results/` tables are the inputs of every number in the paper; the
scripts above regenerate them from scratch.

## Data availability

- Layer 1: all per-run CSVs are in `layer1/results/`.
- Layer 2: per-run CSVs (`3120` validation + `300` calibration) and the analysis
  tables are in `layer2/results/`. The raw per-frame tables (`frames.csv.gz`,
  about 34 MB) stay in the group archive and can be provided on request.

## Provenance and honesty notes

- The two layers use different simulators, parameters, seeds and metrics; their
  absolute percentages are not comparable and each is compared only within its
  own model.
- Layer 1 is the group's earlier Topic 34 model and is used here as motivation
  and as the complete-frame mechanism check.
- Layer 2 is the V3.2 platform: deterministic infeasibility dropping, importance
  exponent alpha, calibration/validation split, EDF-safe strong baseline, queue
  capacities and a burst-failure control.
- No traffic was regenerated and no parameter was re-selected after the
  validation seeds were opened; negative and repeated configurations are
  reported as found.

## Paper build

`paper/build/build.py` renders the DOCX from `content_a.py` and `content_b.py`,
and `paper/build/make_figs.py` regenerates the four figures from the archived
CSVs. Run the scripts from the repository root.
