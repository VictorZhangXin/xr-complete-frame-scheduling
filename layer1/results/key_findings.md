# Topic 34 — 实验结果速览（2026-11-13）

> 数据来自 `sim34` 的完整扫描：4 种策略 × 4 档负载 × 3 档丢包 × 10 个种子，每档 15 s 轨迹。
> 图：`results/fig1_cfr_vs_load.png`、`fig2_iwcfr_waste.png`、`fig3_size_deadline.png`
> 原始数据：`results/summary_*.csv`

---

## 1. 主结果（丢包 1%，高负载 ρ = 0.6）

| 策略 | CFR | 重要性加权 CFR | 浪费的空口 |
|---|---|---|---|
| FIFO | 0.739 | 0.740 | 14.5% |
| EDF | 0.713 | 0.713 | 19.3% |
| **CA-EDF（提出）** | **0.786** | **0.787** | **9.5%** |
| CA-VD（变体） | 0.793 | 0.831 | 6.8% |

**一句话**：在中高负载下，把"来不及完成的帧"提前放弃，能把可用帧比例从 71%（EDF）提高到 79%，同时把浪费的空口从 19% 压到 9.5%。

## 2. 四个发现

**F1 — 收益主要来自"放弃"，不是"排序"。**
EDF → CA-EDF 只改了"是否放弃"这一件事：CFR +7.3 个百分点，浪费减半。
CA-EDF → CA-VD 只改了"先服务谁"：在 ρ=0.6 时 CFR +0.7 pp、加权 +4.4 pp，但**在 ρ=0.5 时 CFR 反而低了 2.8 pp**（0.928 vs 0.956）。
→ 结论：**放弃是稳健的主机制，排序是二阶的、且依赖负载**。报告里应把 CA-EDF 作为主方法，CA-VD 作为"重要性优先"的变体讨论。

**F2 — 帧越大，收益越大。**
（ρ=0.6，p=1%）

| 每帧包数 | FIFO | EDF | CA-EDF | CA-VD |
|---|---|---|---|---|
| 4–6 | 0.893 | 0.902 | 0.919 | 0.895 |
| 6–8 | 0.576 | 0.490 | 0.634 | 0.677 |
| 8–10 | 0.374 | 0.236 | 0.441 | 0.496 |

小帧时放弃几乎无用（帧本来就快完成）；帧越大，"半个帧"浪费的空口越多，提前放弃的价值越明显。这解释了为什么 XR（大帧、多包）特别需要这种调度。

**F3 — 轻负载下三种策略没差别，而且我们的方法会"过度放弃"。**
ρ=0.3 时 FIFO/EDF/CA-EDF 都是 1.000，CA-VD 是 0.998——它丢了 2–4 个本来能完成的帧。
→ 这是真实的代价：可行性判据偏保守时，会误杀边缘帧。报告要写进 limitations。

**F4 — 截止期极紧 + 丢包大时，谁都救不了。**
（ρ=0.6，p=5%，截止期 = 1× 帧间隔）

| 策略 | CFR | 浪费 |
|---|---|---|
| FIFO | 0.630 | 23.4% |
| EDF | 0.604 | 28.6% |
| CA-EDF | 0.665 | 16.4% |
| CA-VD | 0.658 | 14.2% |

全部掉到 0.60–0.67。放弃只能减少浪费，**不能凭空创造可行性**。这就是指南要求的"负面/压力案例"。

## 3. 可直接写进报告的英文句子

- "At a background load of 0.6 and a 1 % packet error rate, giving up on frames that can no longer complete raises the on-time complete-frame ratio from 0.713 (EDF) to 0.786, while reducing wasted airtime from 19.3 % to 9.5 %."
- "An ablation that changes only the service order (CA-VD) adds a further 0.7 percentage points of CFR at high load but loses 2.8 percentage points at moderate load; the benefit of scheduling therefore comes mainly from abandonment, not from ordering."
- "The gain grows with frame size, from 1.7 percentage points for 4–6 packets per frame to 20.5 points for 8–10 packets, which is the regime in which XR traffic operates."
- "When the deadline equals one frame interval and 5 % of packets are lost, all policies fall to 0.60–0.67; abandonment reduces waste but cannot restore feasibility."

## 4. 需要写进 Limitations 的四点

1. 背景业务用"以概率 ρ 占用时隙"近似，不是真实队列；
2. 无编码、无 AMC、无 HARQ 合并，失败即重传；
3. 帧之间相互独立，未建模 I/P 帧依赖；
4. 参数为示意值（仅 60/90 fps 有 3GPP 依据），结论是模型层面的比较，不代表商用系统验证。

## 5. 下一步

- 用 `summary_main.csv` 生成参数表（TABLE I）；
- 三张图对应 §VII 的 Fig. 1–3；
- §VIII 讨论直接用 F3/F4 作为"边界条件"。
