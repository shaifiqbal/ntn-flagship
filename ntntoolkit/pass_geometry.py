"""
Satellite pass geometry over a ground station, via SGP4 (Skyfield).

compute_pass samples elevation, slant range, range-rate and range-acceleration on
a uniform time grid. Passing the same ``start_time`` to several satellites puts
them on one shared absolute grid (used by the constellation code in other weeks).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from skyfield.api import EarthSatellite, load, wgs84

from .nr_tolerances import round_trip_ta_us

ABERDEEN_LAT_DEG: float = 57.1497
ABERDEEN_LON_DEG: float = -2.0943
ABERDEEN_ELEV_M: float = 65.0


@dataclass
class Pass:
    name: str
    step_s: float
    t_s: np.ndarray          # seconds since the first sample
    elev_deg: np.ndarray     # elevation angle
    range_m: np.ndarray      # slant range
    range_rate_m_s: np.ndarray
    range_accel_m_s2: np.ndarray
    ta_us: np.ndarray

    def __len__(self) -> int:
        return int(self.t_s.size)

    @property
    def max_elev_deg(self) -> float:
        return float(self.elev_deg.max())

    @property
    def duration_s(self) -> float:
        return float(self.t_s[-1] - self.t_s[0])


def _timescale():
    return load.timescale()


def build_satellite(line1: str, line2: str, name: str = "SAT", ts=None) -> EarthSatellite:
    ts = ts or _timescale()
    return EarthSatellite(line1, line2, name, ts)


def _ground_station(lat_deg=ABERDEEN_LAT_DEG, lon_deg=ABERDEEN_LON_DEG, elev_m=ABERDEEN_ELEV_M):
    return wgs84.latlon(lat_deg, lon_deg, elev_m)


def compute_pass(
    line1: str,
    line2: str,
    name: str,
    start_offset_s: float,
    duration_s: float,
    step_s: float = 0.5,
    lat_deg: float = ABERDEEN_LAT_DEG,
    lon_deg: float = ABERDEEN_LON_DEG,
    elev_m: float = ABERDEEN_ELEV_M,
    start_time=None,
    ts=None,
) -> Pass:
    """Sample the geometry over [start_offset_s, start_offset_s + duration_s]."""
    ts = ts or _timescale()
    sat = build_satellite(line1, line2, name, ts)
    gs = _ground_station(lat_deg, lon_deg, elev_m)

    epoch = start_time if start_time is not None else sat.epoch
    n = int(round(duration_s / step_s)) + 1
    offsets = start_offset_s + np.arange(n) * step_s          # seconds
    t = ts.tt_jd(epoch.tt + offsets / 86400.0)

    topocentric = (sat - gs).at(t)
    alt, az, dist = topocentric.altaz()
    elev_deg = alt.degrees
    range_m = dist.m.astype(float)

    range_rate = np.gradient(range_m, step_s)
    range_accel = np.gradient(range_rate, step_s)

    ta_us = np.array([round_trip_ta_us(r) for r in range_m])

    t_s = offsets - offsets[0]
    return Pass(
        name=name,
        step_s=step_s,
        t_s=t_s,
        elev_deg=elev_deg,
        range_m=range_m,
        range_rate_m_s=range_rate,
        range_accel_m_s2=range_accel,
        ta_us=ta_us,
    )


def find_passes(
    line1: str,
    line2: str,
    name: str,
    search_hours: float = 6.0,
    coarse_step_s: float = 30.0,
    min_elevation_deg: float = 10.0,
    lat_deg: float = ABERDEEN_LAT_DEG,
    lon_deg: float = ABERDEEN_LON_DEG,
    elev_m: float = ABERDEEN_ELEV_M,
    ts=None,
):
    """Return visible passes as (max_elev_deg, start_offset_s, end_offset_s),
    coarse-scanning from the satellite epoch."""
    ts = ts or _timescale()
    sat = build_satellite(line1, line2, name, ts)
    gs = _ground_station(lat_deg, lon_deg, elev_m)

    n = int(round(search_hours * 3600.0 / coarse_step_s)) + 1
    offsets = np.arange(n) * coarse_step_s
    t = ts.tt_jd(sat.epoch.tt + offsets / 86400.0)
    elev = (sat - gs).at(t).altaz()[0].degrees

    passes = []
    above = elev > min_elevation_deg
    i = 0
    while i < n:
        if above[i]:
            j = i
            while j < n and above[j]:
                j += 1
            seg = elev[i:j]
            passes.append((float(seg.max()), float(offsets[i]), float(offsets[min(j, n - 1)])))
            i = j
        else:
            i += 1
    passes.sort(key=lambda p: p[0], reverse=True)
    return passes
