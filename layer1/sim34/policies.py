"""Scheduling policies: FIFO, EDF, EDF+abandon, and the proposed frame-aware rule."""

from .model import p_complete


def _abandon_infeasible(active, now, params):
    """Drop frames whose estimated completion probability is below theta."""
    alive = []
    for f in active:
        if p_complete(f, now, params) < params.theta:
            f.abandoned = True
            f.pending = 0
        else:
            alive.append(f)
    return alive


def fifo(active, now, params):
    """Packet-level first-in-first-out: oldest frame first, no deadline logic."""
    if not active:
        return None
    return min(active, key=lambda f: (f.arrival, f.fid))


def edf(active, now, params):
    """Earliest-deadline-first at packet level; never gives up early."""
    if not active:
        return None
    return min(active, key=lambda f: (f.deadline, f.arrival, f.fid))


def edf_abandon(active, now, params):
    """Ablation: EDF plus proactive abandonment, same priority as EDF."""
    alive = _abandon_infeasible(active, now, params)
    if not alive:
        return None
    return min(alive, key=lambda f: (f.deadline, f.arrival, f.fid))


def frame_aware(active, now, params):
    """
    Proposed rule: abandon frames that can no longer make it, then serve
    the feasible frame with the highest importance-per-remaining-packet
    ratio (a greedy value-density rule), tie-broken by earliest deadline.
    """
    alive = _abandon_infeasible(active, now, params)
    if not alive:
        return None
    return min(alive, key=lambda f: (-f.weight / f.pending, f.deadline, f.fid))


POLICIES = {
    "FIFO": fifo,
    "EDF": edf,
    "CA-EDF": edf_abandon,     # proposed: completion-aware EDF
    "CA-VD": frame_aware,      # variant: completion-aware value-density
}
