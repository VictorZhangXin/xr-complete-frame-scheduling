"""Sanity checks that must pass before any result is reported."""

from dataclasses import replace

from .model import Params, simulate, make_channel, p_complete, Frame
from .policies import POLICIES


def check(name, condition, detail=""):
    status = "PASS" if condition else "FAIL"
    print(f"[{status}] {name}" + (f"  ({detail})" if detail else ""))
    return condition


def main():
    ok = True

    # 1) No loss, no background traffic -> every frame must be delivered.
    #    This is the "known-answer" test required by the validation guide.
    base = Params(duration_ms=4000, p_loss=0.0, bg_load=0.0, seed=1)
    for name, pol in POLICIES.items():
        r = simulate(base, pol)
        ok &= check(f"no-loss/no-load CFR=1.0 [{name}]",
                    abs(r["cfr"] - 1.0) < 1e-9 and r["waste"] == 0.0
                    and r["abandoned"] == 0,
                    f"cfr={r['cfr']:.4f} waste={r['waste']:.4f}")

    # 2) Conservation: every generated frame is completed, expired,
    #    abandoned, or still queued at the end of the run.
    p = Params(duration_ms=4000, p_loss=0.02, bg_load=0.4, seed=2)
    for name, pol in POLICIES.items():
        r = simulate(p, pol)
        ok &= check(f"frame conservation [{name}]",
                    r["frames"] == r["done"] + r["expired"] + r["abandoned"] + r["unfinished"],
                    f"{r['frames']} = {r['done']}+{r['expired']}+{r['abandoned']}+{r['unfinished']}")

    # 3) Paired channel: two policies under the same seed see the same channel.
    b1, o1 = make_channel(p)
    b2, o2 = make_channel(p)
    ok &= check("channel is deterministic per seed", b1 == b2 and o1 == o2)

    # 4) Determinism of a whole run.
    r1 = simulate(p, POLICIES["CA-VD"])
    r2 = simulate(p, POLICIES["CA-VD"])
    ok &= check("run is deterministic", r1 == r2)

    # 5) p_complete falls as the deadline approaches.
    f = Frame(fid=0, stream="A", arrival=0, deadline=20, n_pkts=5, weight=1, pending=5)
    q = Params(bg_load=0.3, p_loss=0.01)
    early, late = p_complete(f, 0, q), p_complete(f, 18, q)
    ok &= check("p_complete decreases with less time left", early > late,
                f"{early:.3f} > {late:.3f}")

    # 6) A one-packet frame with no loss is delivered in the first slot.
    p2 = Params(duration_ms=50, tf_a=1000, tf_b=1000, pkt_min=1, pkt_max=1,
                p_loss=0.0, bg_load=0.0, d_a=5, d_b=5, seed=3)
    r = simulate(p2, POLICIES["FIFO"])
    ok &= check("single-frame hand check", r["cfr"] == 1.0 and r["frames"] >= 1,
                f"cfr={r['cfr']:.3f} frames={r['frames']}")

    print("\nALL CHECKS PASSED" if ok else "\nSOME CHECKS FAILED")
    return ok


if __name__ == "__main__":
    raise SystemExit(0 if main() else 1)
