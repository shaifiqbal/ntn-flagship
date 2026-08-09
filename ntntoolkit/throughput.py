"""
SNR -> throughput and data-volume metrics over a pass (consolidates Week 9).
Throughput per sample = spectral efficiency (CQI table) x bandwidth.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .link_budget import LinkParams, snr_for_pass
from .mcs_tables import snr_to_cqi, cqi_to_efficiency


@dataclass
class ThroughputResult:
    snr_db: np.ndarray
    cqi: np.ndarray
    throughput_mbps: np.ndarray
    visible_s: float
    peak_mbps: float
    mean_visible_mbps: float
    data_volume_mb: float
    min_elev_deg: float


def throughput_for_pass(pss, params: LinkParams = None, min_elev_deg: float = 10.0):
    params = params or LinkParams()
    snr = snr_for_pass(pss, params)
    cqi = snr_to_cqi(np.where(np.isfinite(snr), snr, -999.0))
    rate_mbps = cqi_to_efficiency(cqi) * params.bandwidth_hz / 1e6

    vis = pss.elev_deg > min_elev_deg
    rate_mbps = np.where(vis, rate_mbps, 0.0)
    cqi = np.where(vis, cqi, 0)

    dt = pss.step_s
    peak = float(rate_mbps.max()) if rate_mbps.size else 0.0
    return ThroughputResult(
        snr_db=snr, cqi=cqi, throughput_mbps=rate_mbps,
        visible_s=float(vis.sum() * dt), peak_mbps=peak,
        mean_visible_mbps=float(rate_mbps[vis].mean()) if vis.any() else 0.0,
        data_volume_mb=float(rate_mbps.sum() * dt / 8.0),
        min_elev_deg=min_elev_deg,
    )


def volume_concentration(result: ThroughputResult, volume_frac: float = 0.5) -> float:
    """Fraction of visible time delivering ``volume_frac`` of the data (fastest first)."""
    r = np.sort(result.throughput_mbps)[::-1]
    total = r.sum()
    if total <= 0:
        return float("nan")
    cum = np.cumsum(r) / total
    k = int(np.searchsorted(cum, volume_frac)) + 1
    n_vis = int((result.throughput_mbps > 0).sum())
    return float(k / max(n_vis, 1))
