"""
Overpass - a live 5G-NTN pass analyzer.

Point it at a ground station; it fetches the live Starlink constellation, finds
the best pass overhead, and shows the full engineering picture - link, throughput,
pre-compensation, handover and latency - plus a schedule of upcoming passes.

Built on ntntoolkit, the engine from the 12-week NTN portfolio. Run locally with
`streamlit run app.py`; deployable free on Streamlit Community Cloud.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from ntntoolkit.link_budget import LinkParams
from ntntoolkit.report import format_report
from ntntoolkit.flagship import analyze_best_pass, dashboard_figure
from ntntoolkit.window import build_window_overview
from ntntoolkit.summary import plain_summary

st.set_page_config(page_title="Overpass - 5G NTN pass analyzer",
                   page_icon="",  layout="wide")

st.markdown("""
<style>
.stApp { background: #0e1117; }
.hero {
  background: linear-gradient(135deg, #161b26 0%, #1c2534 100%);
  border: 1px solid #2a3242; border-radius: 16px;
  padding: 26px 30px; margin-bottom: 22px;
}
.hero h1 { color: #e6e9ef; font-size: 2.5rem; margin: 0; letter-spacing: -1px; }
.hero .tag { color: #4da3ff; font-weight: 600; letter-spacing: 2px; font-size: .8rem; }
.hero p { color: #8b93a7; margin: 8px 0 0 0; font-size: 1.02rem; }
.metric-card {
  background: #161b26; border: 1px solid #2a3242; border-radius: 14px;
  padding: 16px 18px; text-align: left;
}
.metric-card .label { color: #8b93a7; font-size: .8rem; letter-spacing: .5px; text-transform: uppercase; }
.metric-card .value { color: #e6e9ef; font-size: 1.7rem; font-weight: 700; margin-top: 2px; }
.metric-card .sub { color: #4da3ff; font-size: .85rem; }
.src-live { color:#3ddc97; font-weight:600; }
.src-snap { color:#4da3ff; font-weight:600; }
.src-cache { color:#ffb454; font-weight:600; }
</style>
""", unsafe_allow_html=True)

PRESETS = {
    "Aberdeen, UK": (57.1497, -2.0943, 65.0),
    "London, UK": (51.5074, -0.1278, 35.0),
    "New York, USA": (40.7128, -74.0060, 10.0),
    "Singapore": (1.3521, 103.8198, 15.0),
    "Custom": None,
}


@st.cache_data(ttl=3600, show_spinner=False)
def _cached_best(lat, lon, elev, scs):
    link = LinkParams()
    report, pss, source = analyze_best_pass(
        prefer_live=True, lat_deg=lat, lon_deg=lon, elev_m=elev, harq_scs_khz=scs, link=link)
    fig = dashboard_figure(pss, report, link=link)
    return report, fig, source


@st.cache_data(ttl=3600, show_spinner=False)
def _cached_window(lat, lon, elev, hours):
    return build_window_overview(prefer_live=True, lat_deg=lat, lon_deg=lon,
                                 elev_m=elev, search_hours=hours)


def _card(label, value, sub=""):
    sub_html = f'<div class="sub">{sub}</div>' if sub else ""
    st.markdown(
        f'<div class="metric-card"><div class="label">{label}</div>'
        f'<div class="value">{value}</div>{sub_html}</div>',
        unsafe_allow_html=True)


st.sidebar.title("Overpass")
st.sidebar.caption("Live 5G non-terrestrial pass analyzer")

choice = st.sidebar.selectbox("Ground station", list(PRESETS.keys()))
if PRESETS[choice] is None:
    lat = st.sidebar.number_input("Latitude", -90.0, 90.0, 57.1497, format="%.4f")
    lon = st.sidebar.number_input("Longitude", -180.0, 180.0, -2.0943, format="%.4f")
    elev = st.sidebar.number_input("Elevation (m)", 0.0, 5000.0, 65.0)
else:
    lat, lon, elev = PRESETS[choice]
    st.sidebar.write(f"**{lat:.4f}, {lon:.4f}**, {elev:.0f} m")

scs = st.sidebar.selectbox("HARQ sub-carrier spacing (kHz)", [15, 30, 60, 120], index=1)
hours = st.sidebar.slider("Look-ahead window (hours)", 1, 6, 3)
go = st.sidebar.button("Analyze passes", type="primary", use_container_width=True)

st.sidebar.markdown("---")
st.sidebar.caption(
    "Built on ntntoolkit, the engine from a 12-week open NTN portfolio. "
    "RF parameters are indicative, not operator data.")

st.markdown("""
<div class="hero">
  <div class="tag">5G &middot; NON-TERRESTRIAL NETWORKS &middot; LIVE</div>
  <h1>Overpass</h1>
  <p>What a 5G phone would see from a satellite passing overhead &mdash; link quality,
  data rate, sync cost, handover and delay. Real orbital data, one click.</p>
</div>
""", unsafe_allow_html=True)

if not go:
    st.info("Pick a ground station in the sidebar and press Analyze passes.")
    st.stop()

try:
    report, fig, source = _cached_best(lat, lon, elev, scs)
except Exception as e:
    st.error(f"Could not analyze a pass for this location: {e}")
    st.stop()

if source == "celestrak-live":
    st.markdown('<span class="src-live">● live Celestrak data</span>',
                unsafe_allow_html=True)
elif source.startswith("snapshot"):
    when = source[source.find("(") + 1:source.find(")")] if "(" in source else "recent"
    st.markdown(f'<span class="src-snap">● recent snapshot ({when}) · real orbital data</span>',
                unsafe_allow_html=True)
else:
    st.markdown('<span class="src-cache">● sample constellation (illustrative)</span>',
                unsafe_allow_html=True)

tab1, tab2 = st.tabs(["Best pass", f"Upcoming passes ({hours} h)"])

with tab1:
    st.subheader(f"Best pass - {report.satellite}")
    st.markdown(plain_summary(report))
    st.write("")

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        _card("Max elevation", f"{report.max_elev_deg:.1f} deg")
    with c2:
        _card("Peak rate", f"{report.peak_mbps:.1f}", f"Mbps - CQI {report.peak_cqi}")
    with c3:
        _card("Data / pass", f"{report.data_volume_mb:.0f}", "MB")
    with c4:
        _card("Service RTT", f"{report.service_rtt_max_ms:.1f}", "ms")

    st.write("")
    st.pyplot(fig, use_container_width=True)

    with st.expander("Full engineering report"):
        st.code(format_report(report), language="text")

with tab2:
    try:
        rows, wsource = _cached_window(lat, lon, elev, hours)
    except Exception as e:
        st.error(f"Could not build the window overview: {e}")
        rows = []
    if rows:
        df = pd.DataFrame([r.as_row() for r in rows]).rename(columns={
            "satellite": "Satellite", "max_elev_deg": "Max elev (deg)",
            "duration_s": "In view (s)", "peak_mbps": "Peak (Mbps)",
            "data_volume_mb": "Data (MB)", "refresh_rate_hz": "Refresh (Hz)",
            "service_rtt_max_ms": "RTT (ms)", "start_offset_s": "Start (s from now)",
        })
        st.dataframe(df, use_container_width=True, hide_index=True)
        st.caption(f"{len(rows)} passes over the next {hours} h, ranked by peak elevation.")
    else:
        st.warning("No passes found in the selected window.")
