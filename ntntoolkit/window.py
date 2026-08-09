"""
Window overview (the Week-11 extension, delivered in the flagship).

build_pass_report gives a deep report on the single best pass. This adds the other
half: every pass over the next few hours, each with its headline numbers, ranked -
so the app can show a schedule, not just one pass.

Each row is a LIGHT summary (geometry + throughput + refresh rate + RTT); the full
handover context is only computed for the deep single-pass report, to keep the
overview fast.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict

import numpy as np

from .tle_fetch import load_starlink_set
from .pass_geometry import (
    find_passes, compute_pass, _timescale,
    ABERDEEN_LAT_DEG, ABERDEEN_LON_DEG, ABERDEEN_ELEV_M,
)
from .link_budget import LinkParams
from .throughput import throughput_for_pass
from .precomp import required_fixed_rate_hz, timing_limited_fraction
from .delay import delay_profile


@dataclass
class PassSummary:
    satellite: str
    max_elev_deg: float
    duration_s: float
    peak_mbps: float
    data_volume_mb: float
    refresh_rate_hz: float
    service_rtt_max_ms: float
    start_offset_s: float

    def as_row(self) -> dict:
        return asdict(self)


def build_window_overview(
    prefer_live: bool = True,
    limit: int = 40,
    search_hours: float = 3.0,
    lat_deg: float = ABERDEEN_LAT_DEG,
    lon_deg: float = ABERDEEN_LON_DEG,
    elev_m: float = ABERDEEN_ELEV_M,
    step_s: float = 1.0,
    min_elev_deg: float = 10.0,
    link: LinkParams = None,
    max_rows: int = 25,
):
    """Return ``(rows, source)`` - a list of PassSummary sorted by max elevation."""
    link = link or LinkParams()
    ts = _timescale()
    tles, source = load_starlink_set(prefer_live=prefer_live, limit=limit)

    rows = []
    for nm, l1, l2 in tles[:limit]:
        passes = find_passes(l1, l2, nm, search_hours=search_hours,
                             min_elevation_deg=min_elev_deg,
                             lat_deg=lat_deg, lon_deg=lon_deg, elev_m=elev_m, ts=ts)
        for max_elev, start, end in passes:
            pss = compute_pass(l1, l2, nm, start_offset_s=start, duration_s=end - start,
                               step_s=step_s, lat_deg=lat_deg, lon_deg=lon_deg,
                               elev_m=elev_m, ts=ts)
            tp = throughput_for_pass(pss, link, min_elev_deg=min_elev_deg)
            d = delay_profile(pss, min_elev_deg=min_elev_deg)
            rate = required_fixed_rate_hz(pss, min_elev_deg)
            rows.append(PassSummary(
                satellite=nm, max_elev_deg=round(pss.max_elev_deg, 1),
                duration_s=round(pss.duration_s, 0), peak_mbps=round(tp.peak_mbps, 1),
                data_volume_mb=round(tp.data_volume_mb, 0),
                refresh_rate_hz=round(rate, 1),
                service_rtt_max_ms=round(d.max_service_rtt_ms, 1),
                start_offset_s=round(start, 0),
            ))

    rows.sort(key=lambda r: r.max_elev_deg, reverse=True)
    return rows[:max_rows], source
