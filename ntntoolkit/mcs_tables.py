"""
5G NR CQI table (3GPP TS 38.214 Table 5.2.2.1-2) and SNR -> CQI mapping.
Consolidates Week 9. SNR thresholds are representative AWGN 10% BLER values.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class CqiEntry:
    cqi: int
    modulation: str
    efficiency: float
    snr_threshold_db: float


CQI_TABLE = (
    CqiEntry(1, "QPSK", 0.1523, -6.7), CqiEntry(2, "QPSK", 0.2344, -4.7),
    CqiEntry(3, "QPSK", 0.3770, -2.3), CqiEntry(4, "QPSK", 0.6016, 0.2),
    CqiEntry(5, "QPSK", 0.8770, 2.4), CqiEntry(6, "QPSK", 1.1758, 4.3),
    CqiEntry(7, "16QAM", 1.4766, 5.9), CqiEntry(8, "16QAM", 1.9141, 8.1),
    CqiEntry(9, "16QAM", 2.4063, 10.3), CqiEntry(10, "64QAM", 2.7305, 11.7),
    CqiEntry(11, "64QAM", 3.3223, 14.1), CqiEntry(12, "64QAM", 3.9023, 16.3),
    CqiEntry(13, "64QAM", 4.5234, 18.7), CqiEntry(14, "64QAM", 5.1152, 21.0),
    CqiEntry(15, "64QAM", 5.5547, 22.7),
)

_THR = np.array([e.snr_threshold_db for e in CQI_TABLE])
_EFF = np.array([e.efficiency for e in CQI_TABLE])


def snr_to_cqi(snr_db) -> np.ndarray:
    snr = np.asarray(snr_db, float)
    return (snr[..., None] >= _THR).sum(axis=-1).astype(int)


def cqi_to_efficiency(cqi) -> np.ndarray:
    cqi = np.asarray(cqi, int)
    eff = np.zeros(cqi.shape, float)
    nz = cqi > 0
    eff[nz] = _EFF[cqi[nz] - 1]
    return eff
