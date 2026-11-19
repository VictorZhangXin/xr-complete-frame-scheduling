"""
Topic 34 — XR frame-completion scheduling simulator (core model).

Discrete time. One *slot* = 1 ms. In each slot there are `pkts_per_slot`
transmission opportunities; background traffic occupies a slot with
probability `bg_load`, and each transmission fails with probability
`p_loss` and must be retried.

A *frame* (the application unit, analogous to a PDU set) is useful only if
ALL of its packets arrive before its display deadline.
"""

from dataclasses import dataclass
from math import erf, sqrt
import random


# --------------------------------------------------------------------------
# Parameters
# --------------------------------------------------------------------------
@dataclass
class Params:
    seed: int = 0
    duration_ms: int = 15000          # length of the simulated trace
    pkts_per_slot: int = 2            # transmission opportunities per ms
    # Stream A: ~60 fps
    tf_a: int = 16                    # frame interval [ms]
    d_a: int = 24                     # display deadline [ms after arrival]
    # Stream B: ~90 fps, tighter deadline -> EDF differs from FIFO
    tf_b: int = 11
    d_b: int = 16
    # Frame size: uniform in [pkt_min, pkt_max] packets
    pkt_min: int = 4
    pkt_max: int = 8
    p_loss: float = 0.01              # per-transmission packet error rate
    bg_load: float = 0.30             # fraction of slots taken by background traffic
    # Importance: a fraction of frames is "important" (I-frame analogue)
    p_important: float = 0.15
    w_important: int = 3
    # Abandonment threshold: give up when P(complete in time) < theta
    theta: float = 0.05
    # Loss correlation: 0 = independent per opportunity, >0 = Gilbert-Elliott
    # (value = bad->good transition probability; bad state loses every packet)
    burst: float = 0.0

    @property
    def max_deadline(self) -> int:
        return max(self.d_a, self.d_b)


# --------------------------------------------------------------------------
# Frame
# --------------------------------------------------------------------------
@dataclass
class Frame:
    fid: int
    stream: str
    arrival: int
    deadline: int
    n_pkts: int
    weight: int
    pending: int
    done_at: int = -1
    expired: bool = False        # missed its deadline while still queued
    abandoned: bool = False      # deliberately dropped by the scheduler
    attempts: int = 0            # transmission opportunities spent on it

    @property
    def done(self) -> bool:
        return self.done_at >= 0


# --------------------------------------------------------------------------
# Pre-generated randomness (shared by every policy -> paired comparison)
# --------------------------------------------------------------------------
def make_channel(params: Params):
    """Per-slot channel state, identical for all policies under one seed."""
    n = params.duration_ms + params.max_deadline + 20
    rng = random.Random(params.seed * 7919 + 13)
    blocked = [rng.random() < params.bg_load for _ in range(n)]

    if params.burst > 0.0:
        # Gilbert-Elliott: bad state loses every packet, stationary bad
        # probability equals p_loss so the average loss rate is unchanged.
        a = params.burst * params.p_loss / max(1e-9, 1.0 - params.p_loss)
        b = params.burst
        bad, states = False, []
        for _ in range(n):
            u = rng.random()
            if bad:
                if u < b:
                    bad = False
            elif u < a:
                bad = True
            states.append(bad)
        ok = [[not states[i] for _ in range(params.pkts_per_slot)] for i in range(n)]
    else:
        ok = [[rng.random() >= params.p_loss for _ in range(params.pkts_per_slot)]
              for _ in range(n)]
    return blocked, ok


def make_arrivals(params: Params):
    """Frame arrivals, sizes and importance: identical for all policies."""
    rng = random.Random(params.seed * 104729 + 7)
    out = []
    for stream, tf, d in (("A", params.tf_a, params.d_a),
                          ("B", params.tf_b, params.d_b)):
        t = 0
        while t < params.duration_ms:
            n = rng.randint(params.pkt_min, params.pkt_max)
            w = params.w_important if rng.random() < params.p_important else 1
            out.append((t, stream, d, n, w))
            t += tf
    out.sort(key=lambda x: (x[0], x[1]))
    return out


# --------------------------------------------------------------------------
# Probability that a frame still finishes in time
# --------------------------------------------------------------------------
def norm_cdf(x: float) -> float:
    return 0.5 * (1.0 + erf(x / sqrt(2.0)))


def success_rate(params: Params) -> float:
    """Expected fraction of transmission opportunities that deliver a packet."""
    return (1.0 - params.bg_load) * (1.0 - params.p_loss)


def p_complete(f: Frame, now: int, params: Params) -> float:
    """
    Normal approximation of P(at least `pending` packets delivered in time),
    with n = slots left, c = opportunities per slot, r = per-opportunity
    success probability.
    """
    n = f.deadline - now
    if n <= 0:
        return 0.0
    c = params.pkts_per_slot
    r = success_rate(params)
    if r <= 0.0:
        return 0.0
    mu = n * c * r
    var = n * c * r * (1.0 - r)
    if var <= 1e-12:
        return 1.0 if mu >= f.pending else 0.0
    z = (f.pending - 0.5 - mu) / sqrt(var)     # continuity correction
    return 1.0 - norm_cdf(z)


# --------------------------------------------------------------------------
# Main simulation loop
# --------------------------------------------------------------------------
def simulate(params: Params, policy):
    """
    policy(active_frames, now, params) -> Frame | None
    A policy may mark frames as abandoned; it must then clear their `pending`.
    """
    blocked, ok = make_channel(params)
    arrivals = make_arrivals(params)

    frames, active = [], []
    ai = 0
    attempts = 0
    t_end = params.duration_ms + params.max_deadline + 10

    for now in range(t_end):
        # 1) new frames arrive
        while ai < len(arrivals) and arrivals[ai][0] <= now:
            t0, stream, d, n, w = arrivals[ai]
            f = Frame(fid=len(frames), stream=stream, arrival=t0,
                      deadline=t0 + d, n_pkts=n, weight=w, pending=n)
            frames.append(f)
            active.append(f)
            ai += 1

        # 2) frames that missed their deadline are lost
        for f in active:
            if not f.done and not f.expired and not f.abandoned and now >= f.deadline:
                f.expired = True
                f.pending = 0

        # 3) background traffic may block the whole slot
        if now < len(blocked) and blocked[now]:
            continue

        # 4) use every transmission opportunity in this slot
        for k in range(params.pkts_per_slot):
            active = [f for f in active if f.pending > 0]
            if not active:
                break
            f = policy(active, now, params)
            if f is None:
                break
            attempts += 1
            f.attempts += 1
            delivered = ok[now][k] if now < len(ok) else True
            if not delivered:
                continue
            f.pending -= 1
            if f.pending == 0:
                f.done_at = now

    return summarise(frames, attempts)


# --------------------------------------------------------------------------
# Metrics
# --------------------------------------------------------------------------
def summarise(frames, attempts):
    done = [f for f in frames if f.done]
    cfr = len(done) / len(frames) if frames else 0.0

    w_total = sum(f.weight for f in frames)
    iw_cfr = sum(f.weight for f in done) / w_total if w_total else 0.0

    wasted = sum(f.attempts for f in frames if not f.done)
    waste = wasted / attempts if attempts else 0.0

    lat = sorted(f.done_at - f.arrival for f in done)
    lat_mean = sum(lat) / len(lat) if lat else 0.0
    lat_p95 = lat[int(0.95 * (len(lat) - 1))] if lat else 0.0

    per_stream = {}
    for s in ("A", "B"):
        fs = [f for f in frames if f.stream == s]
        per_stream[s] = sum(1 for f in fs if f.done) / len(fs) if fs else 0.0

    return dict(
        frames=len(frames),
        cfr=cfr,
        iw_cfr=iw_cfr,
        waste=waste,
        lat_mean=lat_mean,
        lat_p95=lat_p95,
        abandoned=sum(1 for f in frames if f.abandoned),
        expired=sum(1 for f in frames if f.expired),
        unfinished=sum(1 for f in frames if f.pending > 0 and not f.done),
        done=len(done),
        attempts=attempts,
        cfr_a=per_stream["A"],
        cfr_b=per_stream["B"],
    )
