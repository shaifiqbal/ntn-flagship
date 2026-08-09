"""Tests for the flagship-specific modules (window, flagship helper, summary)."""

import matplotlib
import pandas as pd

from ntntoolkit.link_budget import LinkParams
from ntntoolkit.flagship import analyze_best_pass, dashboard_figure
from ntntoolkit.window import build_window_overview, PassSummary
from ntntoolkit.summary import plain_summary
from ntntoolkit.report import PassReport


def test_analyze_best_pass_returns_report_and_pass():
    report, pss, source = analyze_best_pass(prefer_live=False)
    assert isinstance(report, PassReport)
    assert source == "stored-sample"
    assert len(pss) > 0
    assert report.satellite == pss.name


def test_dashboard_figure_builds():
    report, pss, _ = analyze_best_pass(prefer_live=False)
    fig = dashboard_figure(pss, report)
    assert fig is not None
    assert len(fig.axes) >= 4          # 4 panels (plus twin axis)


def test_window_overview_returns_ranked_rows():
    rows, source = build_window_overview(prefer_live=False, search_hours=3.0)
    assert source == "stored-sample"
    assert len(rows) >= 1
    assert all(isinstance(r, PassSummary) for r in rows)
    elevs = [r.max_elev_deg for r in rows]
    assert elevs == sorted(elevs, reverse=True)      # ranked by elevation


def test_window_rows_convert_to_dataframe():
    rows, _ = build_window_overview(prefer_live=False, search_hours=3.0)
    df = pd.DataFrame([r.as_row() for r in rows])
    assert "satellite" in df.columns and "peak_mbps" in df.columns
    assert len(df) == len(rows)


def test_plain_summary_is_readable_text():
    report, _, _ = analyze_best_pass(prefer_live=False)
    text = plain_summary(report)
    assert report.satellite in text
    assert "minutes" in text and "Mbps" in text
