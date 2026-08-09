"""Integration: the end-to-end pass report."""

import math

import numpy as np

from ntntoolkit import build_pass_report, format_report, PassReport


def _report():
    return build_pass_report(prefer_live=False)


def test_report_builds_offline():
    r = _report()
    assert isinstance(r, PassReport)
    assert r.source == "stored-sample"


def test_pass_fields_sane():
    r = _report()
    assert r.max_elev_deg > 10.0
    assert r.duration_s > 0


def test_link_fields_sane():
    r = _report()
    assert r.snr_min_db <= r.snr_max_db
    assert 0 <= r.peak_cqi <= 15
    assert r.peak_mbps >= r.mean_mbps > 0
    assert r.data_volume_mb > 0
    assert 0.0 < r.half_data_busiest_frac <= 1.0


def test_precomp_fields_sane():
    r = _report()
    assert r.peak_ta_us > 0
    assert r.peak_doppler_hz > 0
    assert 0.0 <= r.timing_limited_frac <= 1.0
    assert r.refresh_rate_hz > 0
    assert r.refreshes_over_pass > 0


def test_delay_and_harq_fields_sane():
    r = _report()
    assert 0 < r.oneway_min_ms <= r.oneway_max_ms
    assert r.service_rtt_max_ms > 0
    assert r.harq_processes_needed >= 1
    assert isinstance(r.harq_stalls_terrestrial, bool)


def test_format_report_contains_all_sections():
    text = format_report(_report())
    for tag in ["PASS", "LINK", "SYNC", "HANDOVER", "DELAY"]:
        assert tag in text
