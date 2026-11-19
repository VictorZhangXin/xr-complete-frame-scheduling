# -*- coding: utf-8 -*-
"""English two-layer paper: sections 7-13, appendix and references."""

BLOCKS_B = [
    ("h1", "VII. PACKET-LEVEL VERSUS FRAME-LEVEL DELIVERY"),

    ("p",
     "Topic 34 asks for an explicit comparison between packet-level success and on-time complete "
     "frames, not only between two frame-aware policies. The V2 scan of the second-layer platform "
     "provides that bridge; it uses the 30 exploration seeds 2000-2029 at 45% background, 10% "
     "attempt failure, size coefficient 0.5 and a 4096-packet queue. Table III is therefore "
     "exploratory coverage, not a result of the frozen V3.2 validation seeds."),

    ("table", "TABLE III. PACKET-LEVEL AND FRAME-LEVEL METRICS ON THE SAME TRACES (%)",
     ["Policy", "Packets", "Complete", "Weighted", "Waste (MB)"],
     [["FIFO", "80.97", "67.69", "67.79", "4.633"],
      ["EDF", "80.97", "67.69", "67.79", "4.633"],
      ["EDF-safe", "78.83", "76.56", "76.62", "2.404"],
      ["FA(0)", "76.09", "79.20", "79.09", "1.924"],
      ["FA(1)", "75.72", "77.92", "84.15", "1.860"]],
     [1.8, 1.6, 1.6, 1.6, 1.6]),

    ("p",
     "FIFO and EDF deliver about 80.97% of packets but complete only 67.69% of frames, whereas "
     "FA(0) delivers about 76.09% of packets and completes about 79.20% of frames. A higher packet "
     "ratio can therefore coexist with a lower application-unit completion rate. The two "
     "percentages have different denominators, packets and frames, so they must not be interpreted "
     "as the probability that a delivered packet forms a frame. FIFO and EDF coincide here because "
     "all frames share the same relative deadline, all packets of a frame arrive together and the "
     "tie-break is identical; we keep both course-required baselines but do not treat them as two "
     "independent pieces of evidence. In the first-layer model the two streams have different "
     "deadlines, so FIFO and EDF can differ."),

    ("p",
     "The V2 main matrix scanned five background levels, two size coefficients and two failure "
     "probabilities. V3.2 narrows the focus to importance strength, queue capacity and correlated "
     "failure, so that the paper does not degenerate into a list of parameter sweeps. The base "
     "scan satisfies the course coverage requirement, while calibration and validation answer the "
     "focused question."),

    ("h1", "VIII. LAYER 2: THE IMPORTANCE-WEIGHTED RULE"),

    ("p",
     "Let r_i(t) be the number of packets still pending and L_i(t) = d_i - t the number of slots "
     "before the deadline. At most one packet can be sent in an available slot, so if "
     "r_i(t) > L_i(t) the frame cannot complete on time even if every remaining slot is available "
     "and every attempt succeeds; the scheduler drops the whole frame. The converse does not hold: "
     "a frame that does not trigger the condition may still fail because of blocking, failed "
     "attempts or competition from other frames."),

    ("p",
     "Among frames that have arrived, are not complete, have not expired and have not been dropped, "
     "the policy serves the frame with the largest score v_i^alpha / (r_i(t) L_i(t)), where v_i is "
     "the frame value and alpha is the importance exponent. Ties go to the earlier deadline and "
     "then to the smaller identifier. Each decision attempts one packet; a success reduces the "
     "remaining count and a failure keeps the packet for a later retry. This is an interpretable "
     "heuristic: a smaller remaining workload, a tighter deadline and a larger value all raise "
     "priority, and the three factors trade off through multiplication and division. It is not a "
     "success-probability estimate and it carries no optimality guarantee."),

    ("p",
     "With alpha = 0 the value term is one and the score becomes the completion-aware but "
     "importance-blind FA(0). With alpha = 1 the value enters linearly and the policy is FA(1). "
     "The selected alpha = 0.125 maps the 4:1 value ratio to about 1.189:1 in the score, a mild "
     "importance preference. The exponent does not discount the evaluation values: every weighted "
     "metric always uses the original 4:1 labels. EDF-safe uses exactly the same infeasibility drop "
     "as FA but orders by earliest deadline; it tests whether the FA score is better than a simpler "
     "completion-aware baseline. FA(0) and EDF-safe answer different questions and are not "
     "substitutes."),

    ("p",
     "To isolate the drop rule, versions of FA(0) and FA(1) with early drop disabled keep expiry "
     "deletion and the original score. In a finite queue, a frame is admitted only if the whole "
     "remaining packet set fits; otherwise it is rejected as a whole and still counted in the "
     "denominator. Frames already in service release queue occupancy as they complete, so "
     "scheduling also affects later admission; capacity effects must be interpreted together with "
     "ordering and early dropping."),

    ("h1", "IX. CALIBRATION AND VALIDATION"),

    ("p",
     "We set an illustrative budget of 2 pp for the average loss of ordinary frames, measured "
     "against FA(0). The budget is a research choice, not a 3GPP value or a service-level "
     "agreement; if no weighted candidate satisfies it, the procedure falls back to alpha = 0. "
     "Calibration uses only seeds 4000-4019 and three 4096-packet scenarios at 30%, 45% and 60% "
     "background, comparing alpha in {0, 0.125, 0.25, 0.5, 1}. A candidate is eligible only if, in "
     "each scenario, the upper end of the paired two-sided 95% interval of the FA(0) minus candidate "
     "ordinary-frame loss does not exceed 2 pp. Eligible candidates are ranked by their mean "
     "weighted gain over the three scenarios, with ties broken towards the smaller alpha."),

    ("table", "TABLE IV. CALIBRATION GRID (SEEDS 4000-4019)",
     ["alpha", "Mean weighted gain (pp)", "Largest loss upper bound (pp)", "Eligible"],
     [["0", "0.00", "0.00", "yes"],
      ["0.125", "1.23", "1.61", "yes"],
      ["0.25", "2.21", "3.17", "no"],
      ["0.5", "3.95", "6.18", "no"],
      ["1", "5.38", "10.45", "no"]],
     [1.3, 2.6, 2.7, 1.6]),

    ("p",
     "Table IV and Fig. 3 summarise the grid. The procedure selects alpha = 0.125 and freezes it before validation. Validation then uses "
     "the unseen seeds 5000-5029: four capacities times three backgrounds give 12 IID "
     "configurations, plus one burst-failure configuration at 45% background and 4096 packets. "
     "Eight policies are compared in each configuration, for 3120 validation runs; calibration adds "
     "300, for 3420 runs in total. The IID validation uses 10% attempt failure and a size "
     "coefficient of 0.5. The burst model keeps the same marginal failure probability but "
     "introduces a correlation parameter of 0.9 and is initialised in its stationary distribution; "
     "it is not fitted to real wireless measurements. All policies share the same input trace, and "
     "the input hash is checked."),

    ("p",
     "Independent seeds prevent direct selection of alpha on the validation runs, but the scenario "
     "distribution is not fully independent: validation reuses the background levels seen in "
     "calibration and adds capacity and correlation variation. The 2 pp rule constrains the mean "
     "interval on the calibration sample; the validation reports whether the budget holds and how "
     "many individual runs exceed it, without treating that as an online guarantee. No adjustment "
     "of alpha is made after seeing validation results."),

    ("fig", "paper/figures/fig3_tradeoff.png",
     "Fig. 3. Calibration trade-off frontier. Each point is one importance exponent; the horizontal "
     "axis is the average loss of ordinary frames and the vertical axis the average weighted gain, "
     "both over the three calibration scenarios. The dashed line is the 2 pp budget, and only "
     "alpha = 0.125 lies to its left among the positive-gain candidates."),

    ("h1", "X. LAYER 2 GAINS AND SERVICE COST"),

    ("p",
     "The representative scenario uses a 4096-packet queue, 45% background and 10% attempt "
     "failure. Table V and Fig. 2 give the 30 validation seeds; FA(0.125) is the policy frozen during "
     "calibration, and the scenario is used to explain the trade-off, while the full 13-scenario "
     "results are kept in the evidence files."),

    ("table", "TABLE V. REPRESENTATIVE LAYER-2 RESULTS (30 SEEDS, %)",
     ["Policy", "Overall", "Weighted", "Important", "Ordinary"],
     [["FA(0)", "78.40", "78.26", "78.07", "78.50"],
      ["FA(0.125)", "78.39", "79.50", "81.04", "77.53"],
      ["FA(1)", "76.86", "83.46", "92.52", "71.82"],
      ["EDF-safe", "76.06", "75.69", "75.18", "76.33"]],
     [1.8, 1.6, 1.6, 1.6, 1.6]),

    ("fig", "paper/figures/fig2_layer2.png",
     "Fig. 2. Layer 2 weighted and ordinary-frame completion in the representative scenario. Bars "
     "are 30-seed means; the difference between FA(0.125) and FA(0) is a shift of service from "
     "ordinary to important frames, not a uniform improvement."),

    ("p",
     "Relative to FA(0), FA(0.125) raises the weighted complete-frame ratio by 1.24 pp [0.97, 1.51] "
     "and lowers the ordinary-frame ratio by 0.97 pp [0.79, 1.15]; the overall ratio changes by "
     "-0.014 pp [-0.158, 0.130], which does not establish either a gain or a loss. The mean wasted "
     "bytes per run fall from 1.8588 MB to 1.8444 MB, but the change in waste share, -0.092 pp "
     "[-0.339, 0.154], crosses zero, so no stable reduction in wasted resources is claimed."),

    ("p",
     "Relative to FA(1), the mild weight gives up 3.95 pp of weighted completion while recovering "
     "5.71 pp [5.10, 6.32] of ordinary-frame completion. This is an explicit value trade-off, not a "
     "case in which all metrics improve. If a service cares only about the weighted objective and "
     "not about ordinary frames, alpha = 0.125 may not be the right choice; this paper studies only "
     "the candidates under the stated budget."),

    ("h1", "XI. STRONG BASELINE AND BOUNDARIES"),

    ("p",
     "In all 13 validation configurations the upper end of the paired interval for the average "
     "ordinary-frame loss against FA(0) stays below 2 pp. Some scenarios nevertheless contain 3 of "
     "30 runs that exceed the budget, so the result is not a per-run guarantee. At 40-packet "
     "capacity and 30% background the weighted change is about -0.006 pp with an interval crossing "
     "zero, so it cannot be written that every scenario gains."),

    ("fig", "paper/figures/fig4_boundaries.png",
     "Fig. 4. Selected policy minus EDF-safe on weighted completion across the 13 validation "
     "configurations, with paired 95% intervals. Labels give queue capacity and background "
     "percentage; the last row is the burst-failure configuration. Negative values mean the "
     "completion-aware EDF baseline is better."),

    ("p",
     "The comparison with EDF-safe, summarised in Fig. 4, is the strongest test because EDF-safe already uses the same "
     "deterministic infeasibility drop and differs only in ordering. At 4096 packets and 45% "
     "background, FA(0.125) is 3.81 pp better on weighted completion [3.10, 4.53]; at 80 packets "
     "and 45% it is 3.34 pp better [2.69, 3.99]; at 40 packets and 45% it is 0.92 pp worse "
     "[-1.13, -0.71]; at 80 packets and 30% it is 0.67 pp worse [-1.02, -0.32]. At 4096 packets and "
     "60% background the advantage reaches 10.31 pp [9.77, 10.86], and the burst configuration at "
     "45% gives 3.62 pp [3.07, 4.17]. The selected policy is therefore better in medium and high "
     "background with sufficient queue capacity, and worse when admission or load leaves little for "
     "the scheduler to reorder."),

    ("table", "TABLE VI. EARLY-DROP ABLATION AT 45% BACKGROUND (WEIGHTED CHANGE, PP)",
     ["Cap.", "FA(0) drop on-off", "FA(1) drop on-off"],
     [["40", "-0.02 [-0.06, 0.02]", "0.03 [-0.02, 0.08]"],
      ["80", "3.90 [3.40, 4.40]", "2.69 [2.28, 3.10]"],
      ["160", "4.52 [4.01, 5.04]", "2.94 [2.59, 3.29]"],
      ["4096", "4.52 [4.01, 5.04]", "2.94 [2.59, 3.29]"]],
     [1.5, 3.35, 3.35]),

    ("p",
     "Table VI reports the ablation that explains the boundary. With a large queue, the deterministic drop contributes "
     "about 4.5 pp of weighted completion for FA(0) and about 2.9 pp for FA(1), both with intervals "
     "away from zero. With a 40-packet queue the effect is negligible and the interval crosses "
     "zero. The first-layer conclusion that early abandonment helps and the second-layer finding "
     "that it helps little in small queues are therefore not contradictory: a different admission "
     "bottleneck changes the set of frames that scheduling can still influence. The 160-packet and "
     "4096-packet configurations produce identical completion metrics for all policies and seeds, "
     "although a few waste-byte values differ; the 13 configurations form ten distinct groups by "
     "the four completion metrics and twelve by the six core metrics, so they are not 13 "
     "independent environments."),

    ("h1", "XII. FAILURE MECHANISMS AND RESOURCE COST"),

    ("p",
     "At 40-packet capacity some frames are larger than the whole queue when they arrive. At 45% "
     "background the 30 seeds generate 21596 frames per policy, of which 923 are structurally "
     "inadmissible, 4.27% of all frames. For FA(0), a further 3993 frames are rejected because the "
     "queue is occupied on arrival; the 4916 overflow frames therefore contain 18.78% oversized "
     "frames. The distinction matters for interpretation: enlarging the queue reduces dynamic "
     "occupancy rejection but also admits frames that could never have been admitted before. A "
     "smaller total overflow alone does not prove more efficient scheduling, and computing "
     "completion only over admitted frames would hide structural rejection, which is why every "
     "reported ratio uses all generated frames as the denominator."),

    ("p",
     "Grouped failure counts also show that the ordinary-frame cost is not merely a change in total "
     "resources. At 45% background and 4096 packets, FA(1) improves important-frame completion "
     "while more ordinary frames are classified as infeasible; because failure status and earlier "
     "ordering interact, this supports a service-shift explanation but does not prove what would "
     "have happened to each frame under the other policy. The service cost discussed here is the "
     "ordinary-frame ratio, the overall ratio and wasted attempts; it is not CPU time, energy or a "
     "proof of user-level fairness."),

    ("h1", "XIII. DISCUSSION AND CONCLUSION"),

    ("p",
     "The two layers support one coherent but bounded statement: targeting complete application "
     "units changes how resource use should be evaluated, and using importance information further "
     "requires an explicit statement of the ordinary service that one is willing to give up. The "
     "first layer establishes the completion motivation through the EDF and CA-EDF contrast; the "
     "second layer isolates importance through the alpha ablation under a fixed score, selects the "
     "exponent on independent calibration seeds, and validates it on unseen seeds with a strong "
     "baseline and capacity boundaries."),

    ("p",
     "This is not a simple concatenation of two independent projects. The first layer keeps only "
     "the model description, one clean contrast and its limitations; the second layer carries the "
     "main weight, fixing the evaluation values, choosing the preference strength, and reporting "
     "the strong baseline and failure boundary. The V2 base scan retains the packet-versus-frame "
     "difference and satisfies the required variation factors without expanding every historical "
     "version in the main text."),

    ("p",
     "Under the 2 pp budget, the calibrated alpha = 0.125 keeps a mild cost in validation: the "
     "overall ratio is approximately unchanged and the weighted ratio improves in the representative "
     "scenario. This does not remove the conflict between total utility and service allocation. "
     "Relative to alpha = 1 it gives up weighted gain to restore ordinary service; relative to "
     "EDF-safe it is still worse at some capacities and loads. The result should be read as a "
     "quantified trade-off and a selection method, not as a universally better scheduler."),

    ("p",
     "The main limitations come from the model. The assumption that all necessary packets must "
     "arrive on time ignores partial decoding, inter-frame dependency and error concealment; "
     "random labels are not measured coding importance; retries without feedback delay, equal "
     "packet sizes and a single queue simplify the wireless process. The three-second arrival "
     "window and the tail drain are a finite-horizon experiment and do not establish long-run "
     "steady-state guarantees. Configurations share seeds and some results repeat, which limits the "
     "breadth of the generalisation evidence. Statistically, the per-item intervals carry no "
     "simultaneous coverage guarantee, the budget and the candidate grid are research settings, and "
     "independent validation prevents direct tuning on the same runs but does not cover every "
     "traffic distribution. Implementation tests and a fresh-environment rerun increase "
     "credibility; they do not replace real wireless measurements or a formal proof for all "
     "possible inputs."),

    ("p",
     "We therefore recommend evaluating both the weighted objective and the ordinary service "
     "metrics once the complete-unit success condition has been defined, and choosing an importance "
     "preference under an acceptable cost. For the course objective, a simple controlled comparison "
     "is enough to answer the question; real traffic labels, partial decoding or measured channels "
     "belong to future work rather than to the premises of this report."),

    ("h1", "AI USE DISCLOSURE"),

    ("p",
     "The authors used AI tools (DeepSeek and GPT) as auxiliary aids. The tools helped check "
     "calculations and derivations, cross-validate results and consistency, "
     "draft and debug parts of the simulation code, structure the argument, and polish the English. "
     "All reported results are outputs of the simulators, were re-run and checked by the authors, "
     "and no data or references were fabricated."),

    ("h1", "APPENDIX. REPRODUCIBILITY"),

    ("p",
     "The tables and figures of this paper are recomputed from archived per-run CSVs. The second-"
     "layer code and result tables are at "
     "https://github.com/VictorZhangXin/xr-complete-frame-scheduling/tree/main/layer2 and the "
     "first-layer simulator at "
     "https://github.com/VictorZhangXin/xr-complete-frame-scheduling/tree/main/layer1. The "
     "case directory stores input copies, source SHA256 values, statistics scripts and the "
     "document builder. The first-layer table uses the 40 runs already replayed against the group's "
     "repository; the second-layer representative results come from the 3120 validation runs "
     "executed after the calibration was frozen. No traffic was regenerated, no parameter was "
     "re-selected and no unfavourable configuration was removed to improve the conclusions."),

    ("p",
     "V3.2 has a complete fresh-environment rerun: Python 3.12.14 with pinned scientific "
     "dependencies reproduced 3420 runs with identical fields and identical decompressed per-frame "
     "records. That rerun is a reproducibility check, not additional independent samples. Tests "
     "pass in normal and optimised modes, including 12288 small exact multi-frame comparisons, of "
     "which 1536 cover alpha = 1/8. The archive keeps the original per-frame audit, the full "
     "13-configuration strong-baseline results, the admission breakdown and the duplicate-config "
     "check."),

    ("refs", [
        "B. Sébire and H. Xu, “eXtended Reality for NR,” 3GPP, Jul. 2023. [Online]. Available: "
        "https://www.3gpp.org/technologies/xr-nr",

        "M. Laha and G.-M. Muntean, “Protocol Data Unit Set-based QoS-aware Downlink Scheduling for "
        "Extended Reality Applications in 6G,” in Proc. IEEE Int. Conf. Commun. (ICC), 2026, pp. "
        "1–6, doi: 10.1109/ICC59461.2026.11588222.",

        "M. Gapeyenko, V. Petrov, S. Paris, A. Marcano, and K. I. Pedersen, “Standardization of "
        "Extended Reality (XR) over 5G and 5G-Advanced 3GPP New Radio,” IEEE Network, vol. 37, no. "
        "4, pp. 22–28, 2023, doi: 10.1109/MNET.003.2300062.",

        "P. Paymard, S. Paris, A. Amiri, T. E. Kolding, F. Sanchez Moya, and K. I. Pedersen, "
        "“PDU-set Scheduling Algorithm for XR Traffic in Multi-Service 5G-Advanced Networks,” in "
        "Proc. IEEE Int. Conf. Commun. (ICC), 2024, pp. 758–763, doi: "
        "10.1109/ICC51166.2024.10622463.",

        "3GPP, “System architecture for the 5G System (5GS),” TS 23.501 V18.8.0, Release 18, Jan. "
        "2025, clauses 5.7.7 and 5.37.5.2.",

        "M. Laha and G.-M. Muntean, “PDU Set-Aware Delay-Reliability-Optimal Downlink Scheduling for "
        "Extended Reality Applications in 6G,” in Proc. Joint EuCNC & 6G Summit, 2026, pp. "
        "348–353, doi: 10.1109/EuCNC/6GSummit68295.2026.11577614.",

        "N. Villegas, A. Larrañaga, L. Diez, K. Koutlia, S. Lagén, and R. Agüero, “Lyapunov-Based "
        "PDU Set-Aware Scheduling for XR Traffic in 5G-Advanced Networks,” in Proc. IEEE GLOBECOM, "
        "2025, pp. 5526–5531, doi: 10.1109/GLOBECOM59602.2025.11432151.",

        "B. Zhao, Q. Sun, N. Li, and C.-L. I, “Lyapunov-Based Completion-Aware Scheduling for PDU "
        "Set-Based Real-Time XR Traffic,” arXiv:2608.05537, 2026. [Preprint, not peer reviewed]",

        "Group report, “Frame-Aware Scheduling for XR Delivery,” EEEN3008J Topic 34, 2026, with "
        "code at https://github.com/VictorZhangXin/eeen3008j-topic34 (fixed commit "
        "ff1ae0d58ed1796ceb383e4e19afcdb49f775726). Group work, not an independent peer-reviewed "
        "source.",
    ]),
]
