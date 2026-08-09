"""
App-facing helpers for the flagship (Overpass).

analyze_best_pass runs the deep report and also returns the pass object so the UI
can plot it. dashboard_figure builds the four-panel matplotlib figure the app and
any script can render.
"""

from __future__ import annotations

import numpy as np
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from .tle_fetch import load_starlink_set
from .pass_geometry import (
    find_passes, compute_pass, build_satellite, _timescale,
    ABERDEEN_LAT_DEG, ABERDEEN_LON_DEG, ABERDEEN_ELEV_M,
)
from .link_budget import LinkParams, snr_for_pass
from .throughput import throughput_for_pass, volume_concentration
from .precomp import (
    safe_interval_s, timing_limited_fraction, required_fixed_rate_hz, refresh_count,
)
from .handover import handover_context
from .delay import delay_profile
from .harq import harq_verdict
from .tcp_model import tcp_verdict
from .report import PassReport


def analyze_best_pass(
    prefer_live: bool = True, limit: int = 40,
    lat_deg: float = ABERDEEN_LAT_DEG, lon_deg: float = ABERDEEN_LON_DEG,
    elev_m: float = ABERDEEN_ELEV_M, step_s: float = 0.5, min_elev_deg: float = 10.0,
    link: LinkParams = None, harq_scs_khz: float = 30.0,
):
    """Return ``(report, pss, source)`` for the best pass over the station."""
    link = link or LinkParams()
    ts = _timescale()
    tles, source = load_starlink_set(prefer_live=prefer_live, limit=limit)

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
    tp = throughput_for_pass(pss, link, min_elev_deg=min_elev_deg)
    snr = snr_for_pass(pss, link)
    fin = snr[np.isfinite(snr)]
    ho = handover_context(pss, tles, nm, start_time, min_elev_deg=min_elev_deg, ts=ts)
    d = delay_profile(pss, min_elev_deg=min_elev_deg)
    rtt = d.max_service_rtt_ms
    hv = harq_verdict(rtt, harq_scs_khz)
    tv = tcp_verdict(tp.peak_mbps, rtt)

    report = PassReport(
        source=source, station=(lat_deg, lon_deg, elev_m),
        satellite=nm, max_elev_deg=pss.max_elev_deg, duration_s=pss.duration_s,
        snr_min_db=float(fin.min()), snr_max_db=float(fin.max()),
        peak_cqi=int(tp.cqi.max()), peak_mbps=tp.peak_mbps, mean_mbps=tp.mean_visible_mbps,
        data_volume_mb=tp.data_volume_mb, half_data_busiest_frac=volume_concentration(tp, 0.5),
        peak_ta_us=float(pss.ta_us[vis].max()),
        peak_doppler_hz=float(np.abs((pss.range_rate_m_s[vis] / 299792458.0) * link.carrier_hz).max()),
        timing_limited_frac=timing_limited_fraction(pss),
        refresh_rate_hz=required_fixed_rate_hz(pss, min_elev_deg),
        refreshes_over_pass=refresh_count(pss, min_elev_deg),
        ho_alternatives=ho.n_alternatives, ho_strongest_frac=ho.strongest_frac,
        ho_cost_swap_frac=ho.cost_aware_swap_frac,
        oneway_min_ms=d.min_oneway_ms, oneway_max_ms=d.max_oneway_ms,
        service_rtt_max_ms=rtt, harq_scs_khz=harq_scs_khz,
        harq_processes_needed=hv.required_processes,
        harq_stalls_terrestrial=hv.stalls_terrestrial,
        tcp_rtt_ms=rtt, tcp_window_limited=tv.limited_by_window,
    )
    return report, pss, source


def dashboard_figure(pss, report, link: LinkParams = None, min_elev_deg: float = 10.0):
    """Build a styled dark-theme four-panel dashboard figure for a pass."""
    link = link or LinkParams()
    vis = pss.elev_deg > min_elev_deg
    t = pss.t_s[vis]
    tp = throughput_for_pass(pss, link, min_elev_deg=min_elev_deg)
    iv = safe_interval_s(pss.range_rate_m_s, pss.range_accel_m_s2)
    d = delay_profile(pss, min_elev_deg=min_elev_deg)

    # palette
    BG = "#0e1117"; PANEL = "#161b26"; GRID = "#2a3242"
    FG = "#e6e9ef"; MUTED = "#8b93a7"
    BLUE = "#4da3ff"; GREEN = "#3ddc97"; PURPLE = "#b48cff"; RED = "#ff6b6b"; AMBER = "#ffb454"

    plt.rcParams.update({
        "figure.facecolor": BG, "axes.facecolor": PANEL, "savefig.facecolor": BG,
        "text.color": FG, "axes.labelcolor": MUTED, "xtick.color": MUTED,
        "ytick.color": MUTED, "axes.edgecolor": GRID, "grid.color": GRID,
        "font.family": "DejaVu Sans", "axes.titleweight": "bold",
    })

    fig, ax = plt.subplots(2, 2, figsize=(12, 8))
    for row in ax:
        for a in row:
            a.set_facecolor(PANEL)
            for s in a.spines.values():
                s.set_color(GRID)
            a.grid(True, alpha=0.25, lw=0.6)
            a.tick_params(labelsize=9)

    # A - pass & data rate (filled)
    a = ax[0, 0]
    a.fill_between(t, tp.throughput_mbps[vis], color=BLUE, alpha=0.18)
    a.plot(t, tp.throughput_mbps[vis], color=BLUE, lw=2.4)
    a.set_ylabel("throughput (Mbps)", color=BLUE, fontsize=10)
    a.set_xlabel("time in pass (s)", fontsize=9)
    a.set_title("A   DATA RATE", color=FG, loc="left", fontsize=12, pad=10)
    ab = a.twinx()
    ab.plot(t, pss.elev_deg[vis], color=AMBER, lw=1.4, ls="--", alpha=0.9)
    ab.set_ylabel("elevation (deg)", color=AMBER, fontsize=10)
    ab.tick_params(labelsize=9, colors=MUTED)
    for s in ab.spines.values():
        s.set_color(GRID)
    a.margins(x=0)

    # B - sync cost (filled)
    b = ax[0, 1]
    b.fill_between(t, iv[vis] * 1000.0, color=GREEN, alpha=0.16)
    b.plot(t, iv[vis] * 1000.0, color=GREEN, lw=2.4)
    b.set_ylabel("safe refresh interval (ms)", color=GREEN, fontsize=10)
    b.set_xlabel("time in pass (s)", fontsize=9)
    b.set_title("B   PRE-COMP SYNC COST", color=FG, loc="left", fontsize=12, pad=10)
    b.margins(x=0)

    # C - latency
    c = ax[1, 0]
    c.fill_between(d.t_s, d.service_rtt_ms, color=PURPLE, alpha=0.16)
    c.plot(d.t_s, d.service_rtt_ms, color=PURPLE, lw=2.4, label="service RTT")
    c.plot(d.t_s, d.e2e_rtt_ms, color=RED, lw=1.6, ls="--", label="end-to-end (est)")
    c.set_ylabel("round-trip time (ms)", color=PURPLE, fontsize=10)
    c.set_xlabel("time in pass (s)", fontsize=9)
    c.set_title("C   LATENCY", color=FG, loc="left", fontsize=12, pad=10)
    leg = c.legend(fontsize=8, facecolor=PANEL, edgecolor=GRID, labelcolor=FG)
    c.margins(x=0)

    # D - report card
    dax = ax[1, 1]
    dax.set_facecolor(PANEL)
    dax.axis("off")
    dax.set_title("D   PASS REPORT", color=FG, loc="left", fontsize=12, pad=10)
    stall = "stalls 16-pool" if report.harq_stalls_terrestrial else "within pool"
    stall_col = RED if report.harq_stalls_terrestrial else GREEN
    rows = [
        ("satellite", report.satellite, FG),
        ("max elevation", f"{report.max_elev_deg:.1f} deg", FG),
        ("in view", f"{report.duration_s:.0f} s", FG),
        ("peak rate", f"{report.peak_mbps:.1f} Mbps  (CQI {report.peak_cqi})", BLUE),
        ("data volume", f"{report.data_volume_mb:.0f} MB / pass", BLUE),
        ("refresh rate", f"{report.refresh_rate_hz:.1f} Hz", GREEN),
        ("timing-limited", f"{report.timing_limited_frac*100:.0f}% of pass", GREEN),
        ("service RTT", f"{report.service_rtt_max_ms:.1f} ms", PURPLE),
        (f"HARQ @{report.harq_scs_khz:.0f}kHz", f"{report.harq_processes_needed} proc ({stall})", stall_col),
    ]
    y = 0.86
    for label, val, col in rows:
        dax.text(0.03, y, label, color=MUTED, fontsize=10.5, va="top", family="DejaVu Sans")
        dax.text(0.52, y, val, color=col, fontsize=10.5, va="top", weight="bold",
                 family="DejaVu Sans Mono")
        y -= 0.095

    fig.tight_layout(pad=1.6)
    return fig
