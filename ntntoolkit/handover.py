"""
Handover context for the hero pass (consolidates Week 8).

For the single best pass, we ask: while this satellite was serving, was it also
the one a handover policy would have chosen? We propagate every other satellite on
the SAME absolute time grid, and at each decision epoch compare the hero against
the concurrently visible alternatives on two axes from Week 8:

  * margin  - relative link budget (shorter range = stronger).
  * sync cost - the pre-comp safe interval (longer = cheaper to keep legal).

We report how often the hero was the strongest-signal choice, and how often a
cost-aware swap (within a margin tolerance, prefer the cheaper-to-sync satellite)
would have picked someone else.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .pass_geometry import compute_pass, build_satellite, _ground_station, _timescale
from .link_budget import LinkParams, fspl_db
from .precomp import safe_interval_s


@dataclass
class HandoverContext:
    n_alternatives: int          # other satellites seen during the hero pass
    strongest_frac: float        # fraction of epochs hero had the best margin
    cost_aware_swap_frac: float  # fraction where cost-aware would pick another sat


def handover_context(
    hero_pass,
    tles,
    hero_name: str,
    start_time,
    decision_dt: float = 5.0,
    min_elev_deg: float = 10.0,
    margin_tol_db: float = 1.0,
    ts=None,
) -> HandoverContext:
    ts = ts or _timescale()
    dur = hero_pass.t_s[-1]
    step = hero_pass.step_s

    # propagate all satellites on the hero's shared grid
    tracks = []
    for nm, l1, l2 in tles:
        p = compute_pass(l1, l2, nm, start_offset_s=0.0, duration_s=dur, step_s=step,
                         start_time=start_time, ts=ts)
        tracks.append((nm, p))

    hero_idx = next((i for i, (nm, _) in enumerate(tracks) if nm == hero_name), None)
    if hero_idx is None:
        return HandoverContext(0, float("nan"), float("nan"))

    margins = np.array([-fspl_db(p.range_m) for _, p in tracks])          # higher = stronger
    intervals = np.array([safe_interval_s(p.range_rate_m_s, p.range_accel_m_s2)
                          for _, p in tracks])
    vis = np.array([p.elev_deg > min_elev_deg for _, p in tracks])

    epochs = np.unique(np.clip(
        np.searchsorted(hero_pass.t_s, np.arange(0, dur + 1e-9, decision_dt)),
        0, len(hero_pass.t_s) - 1))

    strongest = 0
    swap = 0
    counted = 0
    alt_seen = set()
    for i in epochs:
        if not vis[hero_idx, i]:
            continue
        visible = np.where(vis[:, i])[0]
        for v in visible:
            if v != hero_idx:
                alt_seen.add(v)
        counted += 1
        best = visible[np.argmax(margins[visible, i])]
        if best == hero_idx:
            strongest += 1
        # cost-aware: among sats within tol of best margin, pick longest interval
        near = visible[margins[visible, i] >= margins[best, i] - margin_tol_db]
        cost_choice = near[np.argmax(intervals[near, i])]
        if cost_choice != hero_idx:
            swap += 1

    if counted == 0:
        return HandoverContext(len(alt_seen), float("nan"), float("nan"))
    return HandoverContext(
        n_alternatives=len(alt_seen),
        strongest_frac=strongest / counted,
        cost_aware_swap_frac=swap / counted,
    )
