"""
Propagation delay across a pass.

The service link (UE <-> satellite) is fixed by the geometry we already compute:
one-way delay = slant range / c. Two round trips matter:

  * SERVICE-LINK RTT = 2 x one-way. The UE<->satellite radio loop - the delay a
    HARQ process on the access link has to tolerate.
  * END-TO-END RTT (transparent payload) adds the feeder link (satellite <->
    gateway). We do not have the gateway geometry, so the feeder hop is ESTIMATED
    from a nominal gateway slant range; the default assumes a feeder comparable to
    the service link. The service-link RTT is the exactly-known quantity.

All delays are propagation only: no processing, queueing or scheduling delay.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .nr_tolerances import SPEED_OF_LIGHT_M_S


@dataclass
class DelayProfile:
    t_s: np.ndarray
    elev_deg: np.ndarray
    oneway_ms: np.ndarray
    service_rtt_ms: np.ndarray
    e2e_rtt_ms: np.ndarray
    min_oneway_ms: float
    max_oneway_ms: float
    min_service_rtt_ms: float
    max_service_rtt_ms: float


def oneway_delay_ms(range_m) -> np.ndarray:
    """One-way propagation delay (ms) for a slant range in metres."""
    return np.asarray(range_m, float) / SPEED_OF_LIGHT_M_S * 1e3


def delay_profile(pss, feeder_range_m: float | None = None,
                  min_elev_deg: float = 10.0) -> DelayProfile:
    """Delay profile across a pass. ``feeder_range_m`` sets the gateway hop for the
    end-to-end estimate; if None the feeder equals the mean service range."""
    vis = pss.elev_deg > min_elev_deg
    rng = pss.range_m[vis]
    t = pss.t_s[vis]
    elev = pss.elev_deg[vis]

    oneway = oneway_delay_ms(rng)
    service_rtt = 2.0 * oneway

    if feeder_range_m is None:
        feeder_range_m = float(rng.mean())
    feeder_oneway = oneway_delay_ms(np.full_like(rng, feeder_range_m))
    e2e_rtt = 2.0 * (oneway + feeder_oneway)

    return DelayProfile(
        t_s=t, elev_deg=elev, oneway_ms=oneway, service_rtt_ms=service_rtt,
        e2e_rtt_ms=e2e_rtt,
        min_oneway_ms=float(oneway.min()), max_oneway_ms=float(oneway.max()),
        min_service_rtt_ms=float(service_rtt.min()),
        max_service_rtt_ms=float(service_rtt.max()),
    )
