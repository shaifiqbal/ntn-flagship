"""
5G NR / NTN tolerance constants and small conversion helpers, carried across the
portfolio.

  * Cyclic prefix (normal CP, 15 kHz SCS) = 4.69 us. This is the author's chosen
    working timing yardstick, NOT a formally specified 3GPP residual-TA limit.
  * Residual frequency tolerance = 0.1 ppm (TS 38.101-5) -> 200 Hz at 2.0 GHz.
"""

from __future__ import annotations

import numpy as np

SPEED_OF_LIGHT_M_S: float = 299_792_458.0
CYCLIC_PREFIX_US: float = 4.69
FREQ_TOL_PPM: float = 0.1
DEFAULT_CARRIER_HZ: float = 2.0e9


def cyclic_prefix_us(scs_khz: float = 15.0) -> float:
    """Normal-CP cyclic prefix duration (us); scales inversely with SCS."""
    if scs_khz <= 0:
        raise ValueError("SCS must be positive")
    return CYCLIC_PREFIX_US * (15.0 / scs_khz)


def freq_tolerance_hz(carrier_hz: float = DEFAULT_CARRIER_HZ) -> float:
    """Residual carrier-frequency tolerance (Hz) at 0.1 ppm."""
    if carrier_hz <= 0:
        raise ValueError("carrier must be positive")
    return FREQ_TOL_PPM * 1e-6 * carrier_hz


def round_trip_ta_us(range_m: float) -> float:
    """Round-trip timing advance (us) for a one-way slant range."""
    return 2.0 * range_m / SPEED_OF_LIGHT_M_S * 1e6


def doppler_hz(range_rate_m_s: float, carrier_hz: float = DEFAULT_CARRIER_HZ) -> float:
    """Doppler shift (Hz); opening range (positive range-rate) -> negative shift."""
    return -(range_rate_m_s / SPEED_OF_LIGHT_M_S) * carrier_hz
