"""
Downlink budget for a direct-to-handset NTN link (consolidates Weeks 1, 9).

  C/N0 (dB-Hz) = EIRP + G/T - FSPL - L_excess + 228.6
  SNR  (dB)    = C/N0 - 10*log10(bandwidth_Hz)

Indicative S-band direct-to-cell parameters, not operator data - they set the SNR
RANGE across a pass; the analysis is about the shape of the result.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .nr_tolerances import SPEED_OF_LIGHT_M_S, DEFAULT_CARRIER_HZ

BOLTZMANN_TERM_DB = 228.6


@dataclass
class LinkParams:
    eirp_dbw: float = 34.0
    g_over_t_dbk: float = -24.0
    bandwidth_hz: float = 5.0e6
    carrier_hz: float = DEFAULT_CARRIER_HZ
    zenith_excess_db: float = 0.5
    implementation_loss_db: float = 2.0


def fspl_db(range_m, carrier_hz: float = DEFAULT_CARRIER_HZ):
    lam = SPEED_OF_LIGHT_M_S / carrier_hz
    return 20.0 * np.log10(4.0 * np.pi * np.maximum(np.asarray(range_m, float), 1.0) / lam)


def excess_loss_db(elev_deg, zenith_excess_db: float = 0.5):
    e = np.clip(np.asarray(elev_deg, float), 1.0, 90.0)
    return zenith_excess_db / np.sin(np.radians(e))


def snr_db(range_m, elev_deg, params: LinkParams = None):
    params = params or LinkParams()
    cn0 = (params.eirp_dbw + params.g_over_t_dbk - fspl_db(range_m, params.carrier_hz)
           - excess_loss_db(elev_deg, params.zenith_excess_db)
           - params.implementation_loss_db + BOLTZMANN_TERM_DB)
    return cn0 - 10.0 * np.log10(params.bandwidth_hz)


def snr_for_pass(pss, params: LinkParams = None) -> np.ndarray:
    params = params or LinkParams()
    snr = snr_db(pss.range_m, pss.elev_deg, params)
    return np.where(pss.elev_deg > 0.0, snr, -np.inf)
