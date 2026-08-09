"""
The integration layer (Week 11).

build_pass_report ties the whole portfolio together: fetch the constellation, pick
the best pass over a ground station, and run the full chain on it -

  geometry (Wk2-3) -> link budget & throughput (Wk1,9) -> pre-comp refresh cost
  (Wk5-7) -> handover context (Wk8) -> latency / HARQ / TCP (Wk10)

producing ONE PassReport. This is the engine the Week-12 flagship wraps a UI
around. It is a single-best-pass deep report; a window overview (all passes in the
next N hours) is the natural extension.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .tle_fetch import load_starlink_set
from .pass_geometry import (
    find_passes, compute_pass, build_satellite, _timescale,
    ABERDEEN_LAT_DEG, ABERDEEN_LON_DEG, ABERDEEN_ELEV_M,
)
from .nr_tolerances import CYCLIC_PREFIX_US, freq_tolerance_hz, DEFAULT_CARRIER_HZ
from .link_budget import LinkParams, snr_for_pass
from .throughput import throughput_for_pass, volume_concentration
from .precomp import (
    safe_interval_s, timing_limited_fraction, required_fixed_rate_hz, refresh_count,
)
from .handover import handover_context
from .delay import delay_profile
from .harq import harq_verdict
from .tcp_model import tcp_verdict


@dataclass
class PassReport:
    source: str
    station: tuple
    # pass
    satellite: str
    max_elev_deg: float
    duration_s: float
    # link / throughput
    snr_min_db: float
    snr_max_db: float
    peak_cqi: int
    peak_mbps: float
    mean_mbps: float
    data_volume_mb: float
    half_data_busiest_frac: float
    # pre-comp
    peak_ta_us: float
    peak_doppler_hz: float
    timing_limited_frac: float
    refresh_rate_hz: float
    refreshes_over_pass: int
    # handover
    ho_alternatives: int
    ho_strongest_frac: float
    ho_cost_swap_frac: float
    # delay
    oneway_min_ms: float
    oneway_max_ms: float
    service_rtt_max_ms: float
    harq_scs_khz: float
    harq_processes_needed: int
    harq_stalls_terrestrial: bool
    tcp_rtt_ms: float
    tcp_window_limited: bool


def build_pass_report(
    prefer_live: bool = True,
    limit: int = 40,
    lat_deg: float = ABERDEEN_LAT_DEG,
    lon_deg: float = ABERDEEN_LON_DEG,
    elev_m: float = ABERDEEN_ELEV_M,
    step_s: float = 0.5,
    min_elev_deg: float = 10.0,
    link: LinkParams = None,
    harq_scs_khz: float = 30.0,
) -> PassReport:
    link = link or LinkParams()
    ts = _timescale()
    tles, source = load_starlink_set(prefer_live=prefer_live, limit=limit)

    # find the highest pass across the set
    best = None
    for nm, l1, l2 in tles[:limit]:
        ps = find_passes(l1, l2, nm, search_hours=6.0, min_elevation_deg=min_elev_deg,
                         lat_deg=lat_deg, lon_deg=lon_deg, elev_m=elev_m, ts=ts)
        if ps and (best is None or ps[0][0] > best[0]):
            best = (ps[0][0], nm, l1, l2, ps[0][1], ps[0][2])
    if best is None:
        raise ValueError("no visible pass found over the station")
    _, nm, l1, l2, start, end = best

    sat = build_satellite(l1, l2, nm, ts)
    start_time = ts.tt_jd(sat.epoch.tt + start / 86400.0)
    pss = compute_pass(l1, l2, nm, start_offset_s=start, duration_s=end - start,
                       step_s=step_s, lat_deg=lat_deg, lon_deg=lon_deg, elev_m=elev_m, ts=ts)

    vis = pss.elev_deg > min_elev_deg

    # link / throughput
    tp = throughput_for_pass(pss, link, min_elev_deg=min_elev_deg)
    snr = snr_for_pass(pss, link)
    fin = snr[np.isfinite(snr)]
    c50 = volume_concentration(tp, 0.5)

    # pre-comp
    tl_frac = timing_limited_fraction(pss)
    rate = required_fixed_rate_hz(pss, min_elev_deg)
    refr = refresh_count(pss, min_elev_deg)

    # handover context
    ho = handover_context(pss, tles, nm, start_time, min_elev_deg=min_elev_deg, ts=ts)

    # delay / HARQ / TCP
    d = delay_profile(pss, min_elev_deg=min_elev_deg)
    rtt = d.max_service_rtt_ms
    hv = harq_verdict(rtt, harq_scs_khz)
    tv = tcp_verdict(tp.peak_mbps, rtt)

    return PassReport(
        source=source, station=(lat_deg, lon_deg, elev_m),
        satellite=nm, max_elev_deg=pss.max_elev_deg, duration_s=pss.duration_s,
        snr_min_db=float(fin.min()), snr_max_db=float(fin.max()),
        peak_cqi=int(tp.cqi.max()), peak_mbps=tp.peak_mbps, mean_mbps=tp.mean_visible_mbps,
        data_volume_mb=tp.data_volume_mb, half_data_busiest_frac=c50,
        peak_ta_us=float(pss.ta_us[vis].max()),
        peak_doppler_hz=float(np.abs((pss.range_rate_m_s[vis] / 299792458.0) * link.carrier_hz).max()),
        timing_limited_frac=tl_frac, refresh_rate_hz=rate, refreshes_over_pass=refr,
        ho_alternatives=ho.n_alternatives, ho_strongest_frac=ho.strongest_frac,
        ho_cost_swap_frac=ho.cost_aware_swap_frac,
        oneway_min_ms=d.min_oneway_ms, oneway_max_ms=d.max_oneway_ms,
        service_rtt_max_ms=rtt, harq_scs_khz=harq_scs_khz,
        harq_processes_needed=hv.required_processes,
        harq_stalls_terrestrial=hv.stalls_terrestrial,
        tcp_rtt_ms=rtt, tcp_window_limited=tv.limited_by_window,
    )


def format_report(r: PassReport) -> str:
    lat, lon, el = r.station
    L = []
    L.append(f"NTN PASS REPORT  [{r.source}]")
    L.append(f"station: {lat:.4f}, {lon:.4f}, {el:.0f} m")
    L.append("=" * 56)
    L.append(f"PASS      {r.satellite}")
    L.append(f"          max elevation {r.max_elev_deg:.1f} deg, {r.duration_s:.0f} s in view")
    L.append("")
    L.append("LINK      SNR {:.1f}..{:.1f} dB   peak CQI {}   peak {:.1f} Mbps".format(
        r.snr_min_db, r.snr_max_db, r.peak_cqi, r.peak_mbps))
    L.append(f"          mean {r.mean_mbps:.1f} Mbps   volume {r.data_volume_mb:.0f} MB/pass")
    L.append(f"          half the data in the busiest {r.half_data_busiest_frac*100:.0f}% of the time")
    L.append("")
    L.append("SYNC      peak TA {:.0f} us   peak Doppler {:.0f} Hz".format(
        r.peak_ta_us, r.peak_doppler_hz))
    L.append(f"          timing-limited {r.timing_limited_frac*100:.0f}% of the pass")
    L.append(f"          refresh at {r.refresh_rate_hz:.1f} Hz -> {r.refreshes_over_pass} refreshes/pass")
    L.append("")
    if np.isnan(r.ho_strongest_frac):
        L.append(f"HANDOVER  {r.ho_alternatives} alternatives seen (no concurrent decision)")
    else:
        L.append(f"HANDOVER  {r.ho_alternatives} alternatives seen during the pass")
        L.append(f"          hero was strongest-signal {r.ho_strongest_frac*100:.0f}% of the time")
        L.append(f"          cost-aware would swap {r.ho_cost_swap_frac*100:.0f}% of the time")
    L.append("")
    L.append("DELAY     one-way {:.1f}..{:.1f} ms   service RTT {:.1f} ms".format(
        r.oneway_min_ms, r.oneway_max_ms, r.service_rtt_max_ms))
    L.append("          HARQ @ {:.0f} kHz needs {} processes -> {}".format(
        r.harq_scs_khz, r.harq_processes_needed,
        "STALLS terrestrial pool (16)" if r.harq_stalls_terrestrial else "fits terrestrial pool"))
    L.append("          TCP @ peak rate: {}".format(
        "window-limited" if r.tcp_window_limited else "link-limited (window fine)"))
    return "\n".join(L)
