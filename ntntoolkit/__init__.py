"""
ntntoolkit
==========

Week 11 of the NTN portfolio: the integration layer. One package that consolidates
the whole 12-week analysis and runs it end to end on a single real pass.

  pass_geometry, tle_fetch   visibility & orbits        (Wk2-3)
  link_budget, mcs_tables,   SNR -> CQI -> throughput   (Wk1, 9)
    throughput
  precomp                    pre-comp refresh cost      (Wk5-7)
  handover                   handover context           (Wk8)
  delay, harq, tcp_model     latency / HARQ / TCP       (Wk10)
  report                     build_pass_report -> one PassReport tying it together

The Week-12 flagship wraps a UI around build_pass_report.
"""

from .report import PassReport, build_pass_report, format_report

__all__ = ["PassReport", "build_pass_report", "format_report"]
