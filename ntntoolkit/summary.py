"""Plain-language summary of a pass report, for non-technical readers."""

from __future__ import annotations

from .report import PassReport


def plain_summary(r: PassReport) -> str:
    mins = r.duration_s / 60.0
    stall = ("and the delay is already enough to strain 5G's retransmission at "
             "higher speeds" if r.harq_stalls_terrestrial else
             "and the delay stays within what standard 5G can handle")
    return (
        f"**{r.satellite}** rises to **{r.max_elev_deg:.0f}°** above you and stays "
        f"in view for about **{mins:.1f} minutes**. At its best the link carries "
        f"**{r.peak_mbps:.0f} Mbps**, delivering roughly **{r.data_volume_mb:.0f} MB** "
        f"over the whole pass - but half of that arrives in the busiest "
        f"**{r.half_data_busiest_frac*100:.0f}%** of the time, when the satellite is "
        f"high overhead. To stay connected, the phone re-synchronises about "
        f"**{r.refresh_rate_hz:.0f} times a second**, {stall}."
    )
