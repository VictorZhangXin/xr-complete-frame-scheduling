# -*- coding: utf-8 -*-
"""English two-layer paper: title, abstract, sections 1-6."""

TITLE = ("Importance Gains and Service Costs in XR Complete-Frame Delivery: "
         "A Two-Layer Controlled Study")

AUTHORS = ("Zhang Hejie-23219741; Xing Boran-23219740; "
           "Ma Yuanfei-23219752; Li Yujia-23219745")

AUTHOR_NOTE = ("Author order does not reflect the relative contribution of the authors; "
               "all four authors contributed to the group work.")

AFFILIATION = ("EEEN3008J Wireless Communications, Group Project 2026/27, "
               "Beijing-Dublin International College")

ABSTRACT = (
    "XR media frames are segmented into several packets, and a high packet delivery ratio does "
    "not imply a high fraction of usable frames when the application needs every necessary packet "
    "before the display deadline. This paper studies the problem with two complementary "
    "discrete-event experiments. The first layer uses a member's completion-aware model: it keeps "
    "EDF ordering but abandons frames whose estimated completion probability falls below a "
    "threshold, testing whether set-level information improves on-time complete delivery. The "
    "second layer uses the V3.2 platform: with a fixed completion-aware rule, it changes only the "
    "strength of the importance weight and measures the weighted gain, the loss of ordinary "
    "frames, and the wasted resources. In the representative first-layer scenario, CA-EDF raises "
    "the complete-frame ratio by 7.25 percentage points over EDF (paired 95% CI [6.73, 7.76]) and "
    "reduces the share of attempts spent on failed frames by 9.72 points. The second layer selects "
    "alpha = 0.125 on independent calibration seeds; in the 45% background, 4096-packet validation "
    "scenario it raises the weighted complete-frame ratio by 1.24 points [0.97, 1.51] over FA0 and "
    "lowers the ordinary-frame ratio by 0.97 points [0.79, 1.15], while the change in overall "
    "completion crosses zero. In some small-queue scenarios the policy remains worse than EDF-safe. "
    "The results support conditional use of complete-frame information and show that importance "
    "weighting must be reported together with its service cost. The contribution is a reproducible "
    "controlled comparison and a selection procedure, not a claim of global optimality or of "
    "improved subjective XR quality; the two layers use different models and their numbers are "
    "comparable only within each model."
)

BLOCKS_A = [
    ("h1", "I. INTRODUCTION"),

    ("p",
     "Extended Reality (XR) services deliver media as a sequence of frames, each of which must be "
     "displayed within a few milliseconds of its scheduled time. A frame is usually segmented into "
     "several packets, and the receiver can use it only when every necessary packet has arrived. "
     "Packet-level key performance indicators therefore describe the network, not the application: "
     "a system can report a high packet delivery ratio while completing few usable frames, because "
     "the missing packets are concentrated in different frames [1], [2]."),

    ("p",
     "The problem has two questions that are often conflated. The first is whether a scheduler "
     "should reason about complete frames rather than individual packets at all. The second is, "
     "once it does, how strongly it should prefer important frames over ordinary ones, and what "
     "that preference costs. This paper treats them as two layers of one study: the first layer "
     "establishes the motivation with a minimal completion-aware rule, and the second layer "
     "isolates the importance weight inside a fixed scoring structure and measures the trade-off "
     "against a loss budget."),

    ("p",
     "The two layers use different simulators and are therefore not a single system on which one "
     "algorithm is upgraded. The first layer is the group's earlier Topic 34 study: two "
     "periodic streams with different deadlines, FIFO, EDF, a completion-aware EDF (CA-EDF) and a "
     "value-density variant. The second layer is the V3.2 platform developed for this paper: four "
     "60 fps sources, a common 12 ms deadline, four queue capacities, a parameterised score with "
     "importance exponent alpha, a deterministic infeasibility rule, an EDF-safe strong baseline, "
     "a calibration/validation split and a burst-failure control. Numbers from the two layers are "
     "never compared with each other; each is compared only within its own model."),

    ("p",
     "The contributions are: (i) a controlled demonstration that abandoning frames which cannot "
     "complete raises the on-time complete-frame ratio in a two-stream heterogeneous-deadline "
     "model; (ii) a second-layer design in which only the importance exponent changes, so that the "
     "effect of importance is separated from the effect of completion-aware ordering and dropping; "
     "(iii) a reproducible selection procedure that freezes alpha on calibration seeds and "
     "validates it on unseen seeds; and (iv) a boundary analysis that reports where the selected "
     "policy loses to a simpler strong baseline, including small queues, light load and admission "
     "limits. The paper does not claim a new optimal scheduler, and it does not compare against a "
     "re-implementation of PiXR [2]."),

    ("h1", "II. RELATED WORK AND POSITION"),

    ("p",
     "3GPP provides the background. The XR overview [1] explains that application data can consist "
     "of related units and that the network may exploit their relations and relative importance. "
     "Release 18 of TS 23.501 [3] distinguishes set-level delay and error budgets, integrated "
     "handling information, and the relative importance of a set. This distinction matters here: "
     "completeness defines what counts as a usable delivery, while importance decides how to rank "
     "several usable deliveries when resources are short. Our frame is a modelling mapping of a "
     "PDU set, not a claim that every XR media unit has the same dependency structure."),

    ("p",
     "PiXR [2] tracks the remaining delay budget of each PDU set and allocates resources using "
     "urgency and instantaneous channel information. Our model borrows the set-level deadline and "
     "the idea of a trade-off under scarcity, but it does not implement PiXR, and we do not claim "
     "to improve it. Gapeyenko et al. [4] relate XR traffic, delay budgets and system capacity and "
     "discuss application-aware scheduling; their system-level evaluation is richer than our "
     "single-queue abstraction, so their capacity numbers are not transferred. Paymard et al. [5] "
     "use PDU-set context in a multi-service, multi-cell scheduler; this supports the general "
     "direction but is not a performance benchmark for us."),

    ("p",
     "Three further sources inform the design without adding reproduction work. PaDXR [6] "
     "formulates set-level QoS with differentiated reliability and requires care about future "
     "arrival and channel assumptions. The Lyapunov approach of Villegas Saiz et al. [7] uses "
     "virtual queues and a fuller network simulation; it reminds us that remaining work and "
     "deadline must be considered together. Zhao et al. [8] explicitly consider completion "
     "opportunity and long-term reliability debt; this source is a 2026 preprint and is cited as "
     "context only."),

    ("p",
     "Across these works, completeness, urgency, completion opportunity and importance are "
     "different quantities. To avoid mixing several mechanisms, we keep the remaining-packet term, "
     "the remaining-time term and the drop rule fixed, and change only the importance exponent. "
     "All policies are evaluated with the same ground-truth value labels, so a change in the "
     "evaluation standard cannot be mistaken for an algorithmic gain. The paper does not attempt "
     "to reproduce every reference algorithm, and the number of references is not treated as a "
     "measure of completeness."),

    ("h1", "III. TWO-LAYER DESIGN AND MODEL DIFFERENCES"),

    ("p",
     "Both layers treat a frame as a set of necessary packets. The first layer is the group's "
     "earlier Topic 34 study [9] and the second is the V3.2 platform. A frame counts as delivered only if "
     "all its packets are received before its own deadline; every policy in a layer sees the same "
     "arrival and service trace generated from a given seed, and no policy sees future outcomes. "
     "Table I summarises the differences. The first layer has two streams with periods of 16 ms and "
     "11 ms and deadlines of 24 ms and 16 ms, 1 ms slots and two transmission opportunities per "
     "available slot, frame sizes uniform on 4-8 packets, 15% important frames with value 3 against "
     "1, and no finite queue admission. The second layer has four 60 fps sources with random phase "
     "and jitter, a common 12 ms relative deadline, 0.125 ms slots with one opportunity per "
     "available slot, lognormal frame sizes clipped to 2-100 packets, 25% important frames with "
     "value 4 against 1, and queue capacities of 40, 80, 160 or 4096 packets with whole-frame "
     "admission."),

    ("table", "TABLE I. THE TWO MODELS",
     ["Dimension", "Layer 1", "Layer 2 (V3.2)"],
     [["Time and opportunities", "1 ms slots, 2 attempts per available slot", "0.125 ms slots, 1 attempt"],
      ["Traffic sources", "2 periodic streams, 16 and 11 ms", "4 sources, 60 fps, random phase/jitter"],
      ["Relative deadline", "24 ms and 16 ms", "12 ms for all frames"],
      ["Frame size", "Uniform integer 4-8 packets", "Lognormal, rounded and clipped to 2-100"],
      ["Importance", "15% important, value 3:1", "25% important, value 4:1"],
      ["Queue admission", "None", "40, 80, 160, 4096 packets, whole-frame"],
      ["Early drop", "P(complete) < 0.05 (heuristic)", "remaining packets > remaining slots"],
      ["Main comparison", "EDF vs CA-EDF", "FA0 vs FA(alpha), plus EDF-safe"],
      ["Observation window", "15 s arrivals plus tail", "3 s arrivals plus tail"]],
     [2.0, 3.0, 3.2]),

    ("p",
     "The two periods of the first layer correspond to about 62 and 91 frames per second, not "
     "exactly to 60 and 90; the difference follows from the 1 ms slot granularity [9]. Because the "
     "time scale, service volume, deadline, frame size and value model all differ, the layers form "
     "a progression of research questions rather than a sequence of upgrades on one system. The "
     "78.55% complete-frame ratio of the first layer and any percentage of the second layer are "
     "not comparable as absolute quality."),

    ("p",
     "The second layer uses a default mean of 20 packets per frame, a size coefficient of variation "
     "of 0.5 before rounding, and 1200 bytes per packet. Arrival jitter is Gaussian with standard "
     "deviation 1 ms, clipped to plus or minus 4 ms; frame size and importance label are independent "
     "in the main model. Rounding and clipping shift the realised mean and coefficient of variation "
     "slightly, so the archive stores the actual statistics. Background load is the probability "
     "that a slot cannot be used for XR service; it is not a measured bandwidth utilisation. A "
     "failed attempt leaves the packet pending for retry, but the model has no HARQ feedback delay, "
     "link adaptation, multi-user channel difference, coding dependency or display process. Burst "
     "failure is used only to test sensitivity to temporal correlation."),

    ("h1", "IV. METRICS AND STATISTICAL UNITS"),

    ("p",
     "Let N be the number of frames generated in a run and v_i the value of frame i. The indicator "
     "X_i is one when every necessary packet of frame i is delivered before its deadline and zero "
     "otherwise. Frames that are not admitted, are abandoned, or expire remain in the denominator. "
     "The overall complete-frame fraction F and the weighted fraction F_v are the unweighted and "
     "value-weighted means of X_i. The important-frame and ordinary-frame fractions use their own "
     "generated frames as denominators. The number of completed frames is retained as a count, but "
     "cross-seed statistics use per-run ratios; hundreds of frames inside one trace are not treated "
     "as independent replications."),

    ("p",
     "The packet delivery ratio is the number of successfully delivered packets divided by all "
     "generated packets; a retry adds a delivery only when it succeeds. Let A_i be all transmission "
     "attempts spent on frame i and B = 1200 bytes per attempt. The wasted bytes on failed frames "
     "and their share are A_i B summed over frames that never complete, divided by the total "
     "attempted bytes. This waste includes packets successfully received inside failed frames and "
     "failed retransmissions; retransmissions of successfully completed frames are a separate cost "
     "and are not counted as failed-frame waste. The first layer did not specify a packet length, "
     "so it reports attempt shares; the second layer reports bytes and shares, and no artificial "
     "packet length is attached to the first layer."),

    ("p",
     "The resource identity is checked in every run: attempted bytes equal the useful payload of "
     "completed frames plus the retransmission bytes of completed frames plus the attempted bytes "
     "on failed frames. This identity validates the accounting implementation; it does not prove "
     "that a policy is optimal. The statistics use the paired difference delta_j between two "
     "policies on the same seed j. The reported interval is the two-sided 95% Student t interval of "
     "the paired mean, with n = 10 in the first layer and n = 30 in the second. Differences are "
     "reported in percentage points: 1.24 pp means a change of 0.0124 in a fraction, not a relative "
     "increase of 1.24%. Error bars in single-policy plots are intervals of each mean; policy "
     "differences are judged from paired intervals, not from whether two mean intervals overlap."),

    ("p",
     "The 13 configurations of the second layer share calibration and validation seeds and are not "
     "13 independent environments; their intervals are per-item descriptions without simultaneous "
     "coverage correction. The V2 exploration results and the unseen-seed validation results are "
     "reported separately."),

    ("h1", "V. LAYER 1: COMPLETION-AWARE ABANDONMENT"),

    ("p",
     "The first layer compares FIFO, EDF, CA-EDF and CA-VD [9]. FIFO serves the earliest arrival; "
     "EDF serves the earliest deadline; CA-EDF keeps EDF ordering but first removes frames whose "
     "estimated completion probability is below a threshold; CA-VD also replaces the ordering by "
     "value divided by remaining packets. The EDF and CA-EDF pair is therefore the clean mechanism "
     "contrast, while CA-VD is a joint variant whose difference cannot be attributed to importance "
     "alone."),

    ("p",
     "The member implementation treats the remaining slots multiplied by the opportunities per slot "
     "as the potential number of attempts, builds a binomial model with the average probability "
     "that a slot is not blocked and an attempt succeeds, and applies a normal approximation with a "
     "continuity correction. The threshold is 0.05. This estimate ignores queue contention and does "
     "not exactly handle the fact that the two opportunities in a slot share the same background "
     "state. The paper therefore calls the rule an approximate-completion abandonment, not a proof "
     "that a frame is physically impossible. A simple counterexample makes the difference concrete: "
     "one slot, two opportunities, background probability 0.5, no transmission failure and two "
     "remaining packets give a true no-contention completion probability of 0.5, while the code "
     "approximation is about 0.23975. A low estimated probability is not the same concept as "
     "physical infeasibility."),

    ("p",
     "This limitation does not invalidate the simulated gain, because the service process still "
     "follows the generated trace; it limits the theoretical interpretation of the drop rule. The "
     "first layer can show that, under these inputs, the heuristic improves completion, but it "
     "cannot show that it identifies every impossible frame. The representative scenario uses 60% "
     "background blocking and 1% attempt failure; ten paired seeds are used, and the 40 runs were "
     "replayed against the archived CSV before this paper recomputed the paired intervals."),

    ("h1", "VI. LAYER 1 RESULTS AND THE MOVE TO LAYER 2"),

    ("table", "TABLE II. LAYER 1 REPRESENTATIVE SCENARIO (10 SEEDS, %)",
     ["Policy", "CFR", "W-CFR", "Waste", "A", "B"],
     [["FIFO", "73.93", "73.96", "14.50", "95.59", "59.03"],
      ["EDF", "71.31", "71.33", "19.25", "72.58", "70.43"],
      ["CA-EDF", "78.55", "78.71", "9.54", "79.79", "77.71"],
      ["CA-VD", "79.30", "83.14", "6.82", "84.08", "76.00"]],
     [1.7, 1.35, 1.35, 1.25, 1.25, 1.25]),

    ("p",
     "In Table II, A and B are the two streams and waste is the share of attempts spent on "
     "failed frames. Table II and Fig. 1 report the ten-seed means. CA-EDF raises the complete-frame ratio over EDF by 7.25 "
     "pp [6.73, 7.76], the weighted ratio by 7.37 pp [6.73, 8.02], and lowers the wasted-attempt "
     "share by 9.72 pp [9.19, 10.24]. Because the ordering is identical in the two policies, this "
     "difference supports the practical value of selective early abandonment. EDF is not better "
     "than FIFO in this model; the usual optimality statement for EDF has specific premises and "
     "does not apply directly to a problem with dropping, random service and multi-packet "
     "completion reward."),

    ("fig", "paper_two_layer/figs/fig1_layer1.png",
     "Fig. 1. Layer 1 complete-frame ratio in the representative scenario. Bars are ten-seed means "
     "with per-mean 95% t intervals; the 60% background and 1% attempt-failure setting is the same "
     "as in Table II."),

    ("p",
     "CA-VD has a higher weighted ratio than CA-EDF, but this cannot be read as an importance "
     "effect: moving from deadline ordering to value divided by remaining work also introduces a "
     "remaining-work preference, and the two rules can choose different frames even when all "
     "weights are equal. The second layer therefore needs a stricter contrast: keep the same "
     "completion-aware score and the same physical drop rule, and change only the exponent of the "
     "value term. The first layer motivates the mechanism; the second layer addresses attribution "
     "and cost."),
]
