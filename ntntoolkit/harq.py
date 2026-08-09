"""
What the propagation delay does to 5G NR HARQ.

NR uses stop-and-wait HARQ across a fixed pool of parallel processes. To keep a
link busy while waiting for an ACK you need roughly one in-flight process per slot
of round-trip delay. Terrestrial RTT is a few slots, so 16 processes is plenty. A
LEO round trip spans far more slots, so the same pool stalls - which is why 3GPP
Rel-17 NTN raised the process count (up to 32) and added the option to DISABLE
HARQ feedback and lean on higher-layer retransmission.

Slot length depends on the numerology: slot = 1 ms / 2^mu, SCS = 15 kHz*2^mu.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

TERRESTRIAL_HARQ_PROCESSES = 16
NTN_REL17_HARQ_PROCESSES = 32


def slot_duration_ms(scs_khz: float = 15.0) -> float:
    mu = np.log2(scs_khz / 15.0)
    if abs(mu - round(mu)) > 1e-6 or mu < 0:
        raise ValueError("SCS must be 15 kHz * 2^mu (15, 30, 60, 120, ...)")
    return 1.0 / (2.0 ** round(mu))


def slots_in_rtt(rtt_ms, scs_khz: float = 15.0) -> np.ndarray:
    return np.asarray(rtt_ms, float) / slot_duration_ms(scs_khz)


def required_harq_processes(rtt_ms, scs_khz: float = 15.0) -> np.ndarray:
    return np.ceil(slots_in_rtt(rtt_ms, scs_khz)).astype(int)


@dataclass
class HarqVerdict:
    scs_khz: float
    slot_ms: float
    rtt_ms: float
    slots_in_rtt: float
    required_processes: int
    stalls_terrestrial: bool
    stalls_ntn: bool


def harq_verdict(rtt_ms: float, scs_khz: float = 15.0) -> HarqVerdict:
    slot = slot_duration_ms(scs_khz)
    n_slots = float(rtt_ms / slot)
    req = int(np.ceil(n_slots))
    return HarqVerdict(
        scs_khz=scs_khz, slot_ms=slot, rtt_ms=rtt_ms, slots_in_rtt=n_slots,
        required_processes=req,
        stalls_terrestrial=req > TERRESTRIAL_HARQ_PROCESSES,
        stalls_ntn=req > NTN_REL17_HARQ_PROCESSES,
    )
