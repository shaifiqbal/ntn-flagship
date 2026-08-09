"""
Pre-compensation refresh cost (consolidates Weeks 5-7).

A UE holds a GNSS-assisted timing-advance and Doppler correction and must refresh
it before the held value drifts past the 3GPP budgets:

  * timing: residual TA drift must stay inside the cyclic prefix (4.69 us working
    yardstick). dTA/dt = 2*range_rate/c, so T_timing = CP / |dTA/dt|.
  * frequency: residual Doppler drift must stay inside the +/-0.1 ppm tolerance
    (200 Hz at 2 GHz). dDoppler/dt = -(range_accel/c)*fc, so T_freq = df_tol /
    |dDoppler/dt|.

The safe interval is the tighter of the two (times a safety factor). Near the
horizon range-rate is large so TIMING binds; near zenith range-rate falls and
range-acceleration peaks so FREQUENCY binds - the constraint hand-off from Week 6.
"""

from __future__ import annotations

import numpy as np

from .nr_tolerances import (
    SPEED_OF_LIGHT_M_S,
    CYCLIC_PREFIX_US,
    DEFAULT_CARRIER_HZ,
    freq_tolerance_hz,
)


def timing_interval_s(range_rate_m_s, cp_us: float = CYCLIC_PREFIX_US) -> np.ndarray:
    """Safe hold time (s) set by the timing budget."""
    rr = np.abs(np.asarray(range_rate_m_s, float))
    dta_dt = 2.0 * rr / SPEED_OF_LIGHT_M_S            # s per s
    return np.where(dta_dt > 0, (cp_us * 1e-6) / np.maximum(dta_dt, 1e-30), np.inf)


def freq_interval_s(range_accel_m_s2, carrier_hz: float = DEFAULT_CARRIER_HZ) -> np.ndarray:
    """Safe hold time (s) set by the frequency budget."""
    ra = np.abs(np.asarray(range_accel_m_s2, float))
    ddop_dt = (ra / SPEED_OF_LIGHT_M_S) * carrier_hz   # Hz per s
    tol = freq_tolerance_hz(carrier_hz)
    return np.where(ddop_dt > 0, tol / np.maximum(ddop_dt, 1e-30), np.inf)


def safe_interval_s(range_rate_m_s, range_accel_m_s2, safety: float = 0.5,
                    cp_us: float = CYCLIC_PREFIX_US,
                    carrier_hz: float = DEFAULT_CARRIER_HZ) -> np.ndarray:
    """Closed-form safe refresh interval: safety * min(timing, frequency)."""
    t_ta = timing_interval_s(range_rate_m_s, cp_us)
    t_fr = freq_interval_s(range_accel_m_s2, carrier_hz)
    return safety * np.minimum(t_ta, t_fr)


def timing_limited_fraction(pss, **kwargs) -> float:
    """Fraction of the pass where the timing budget is the binding one."""
    t_ta = timing_interval_s(pss.range_rate_m_s, kwargs.get("cp_us", CYCLIC_PREFIX_US))
    t_fr = freq_interval_s(pss.range_accel_m_s2, kwargs.get("carrier_hz", DEFAULT_CARRIER_HZ))
    return float((t_ta <= t_fr).mean())


def required_fixed_rate_hz(pss, min_elev_deg: float = 10.0, **kwargs) -> float:
    """Worst-case fixed refresh RATE (Hz) needed to stay legal over the pass."""
    vis = pss.elev_deg > min_elev_deg
    iv = safe_interval_s(pss.range_rate_m_s[vis], pss.range_accel_m_s2[vis], **kwargs)
    return float(1.0 / iv.min()) if iv.size else float("nan")


def refresh_count(pss, min_elev_deg: float = 10.0, **kwargs) -> int:
    """Refreshes over the visible pass at the worst-case fixed rate."""
    vis = pss.elev_deg > min_elev_deg
    if not vis.any():
        return 0
    dur = pss.t_s[vis][-1] - pss.t_s[vis][0]
    rate = required_fixed_rate_hz(pss, min_elev_deg, **kwargs)
    return int(np.ceil(dur * rate))
