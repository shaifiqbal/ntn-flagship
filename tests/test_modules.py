"""Consolidated module checks (precomp, throughput, link budget, handover)."""

import numpy as np

from ntntoolkit.tle_fetch import load_starlink_set
from ntntoolkit.pass_geometry import find_passes, compute_pass, build_satellite, _timescale
from ntntoolkit.link_budget import LinkParams, snr_db, fspl_db
from ntntoolkit.throughput import throughput_for_pass, volume_concentration
from ntntoolkit.precomp import (
    safe_interval_s, timing_interval_s, freq_interval_s, timing_limited_fraction,
)
from ntntoolkit.mcs_tables import snr_to_cqi


def _hero():
    ts = _timescale()
    tles, _ = load_starlink_set(prefer_live=False)
    best = None
    for nm, l1, l2 in tles:
        ps = find_passes(l1, l2, nm, search_hours=6.0, min_elevation_deg=10.0, ts=ts)
        if ps and (best is None or ps[0][0] > best[0]):
            best = (ps[0][0], nm, l1, l2, ps[0][1], ps[0][2])
    _, nm, l1, l2, start, end = best
    return compute_pass(l1, l2, nm, start_offset_s=start, duration_s=end - start, step_s=0.5, ts=ts)


def test_snr_falls_with_range():
    p = LinkParams()
    assert snr_db(500e3, 90.0, p) > snr_db(2000e3, 90.0, p)


def test_snr_to_cqi_monotonic():
    cqi = snr_to_cqi(np.linspace(-15, 30, 100))
    assert np.all(np.diff(cqi) >= 0)


def test_safe_interval_positive():
    p = _hero()
    iv = safe_interval_s(p.range_rate_m_s, p.range_accel_m_s2)
    assert np.all(iv > 0)


def test_timing_binds_when_range_rate_large():
    # large range-rate, tiny accel -> timing interval shorter than frequency
    assert timing_interval_s(6000.0) < freq_interval_s(0.5)


def test_timing_limited_fraction_in_range():
    p = _hero()
    f = timing_limited_fraction(p)
    assert 0.0 <= f <= 1.0


def test_throughput_and_concentration():
    p = _hero()
    tp = throughput_for_pass(p, LinkParams(), min_elev_deg=10.0)
    assert tp.peak_mbps >= tp.mean_visible_mbps > 0
    c = volume_concentration(tp, 0.5)
    assert 0.0 < c <= 0.5 + 1e-6
