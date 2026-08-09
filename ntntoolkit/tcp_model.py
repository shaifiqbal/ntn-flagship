"""
What the delay does to TCP throughput.

A TCP sender can have at most one receive-window of unacknowledged data in flight,
so throughput <= window / RTT. To fill a link you need a window at least as large
as the bandwidth-delay product (BDP = rate x RTT). On a LEO link the RTT is large
enough that the classic 64 KB window (no window scaling) caps throughput far below
the available rate - the bottleneck becomes latency, not bandwidth.
"""

from __future__ import annotations

from dataclasses import dataclass

DEFAULT_TCP_WINDOW_BYTES = 65_535


def bdp_bytes(rate_bps: float, rtt_ms: float) -> float:
    return rate_bps * (rtt_ms / 1000.0) / 8.0


def window_limited_throughput_mbps(window_bytes, rtt_ms):
    import numpy as np
    return (np.asarray(window_bytes, float) * 8.0) / (np.asarray(rtt_ms, float) / 1000.0) / 1e6


@dataclass
class TcpVerdict:
    rate_mbps: float
    rtt_ms: float
    bdp_kb: float
    default_window_cap_mbps: float
    limited_by_window: bool
    utilisation_pct: float


def tcp_verdict(rate_mbps: float, rtt_ms: float,
                window_bytes: float = DEFAULT_TCP_WINDOW_BYTES) -> TcpVerdict:
    rate_bps = rate_mbps * 1e6
    bdp = bdp_bytes(rate_bps, rtt_ms)
    cap = float(window_limited_throughput_mbps(window_bytes, rtt_ms))
    achieved = min(cap, rate_mbps)
    return TcpVerdict(
        rate_mbps=rate_mbps, rtt_ms=rtt_ms, bdp_kb=bdp / 1024.0,
        default_window_cap_mbps=cap, limited_by_window=cap < rate_mbps,
        utilisation_pct=100.0 * achieved / rate_mbps if rate_mbps > 0 else 0.0,
    )
