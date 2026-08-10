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
    # ---- United Kingdom ----
    "Aberdeen, UK": (57.1497, -2.0943, 65.0),
    "Belfast, UK": (54.5973, -5.9301, 6.0),
    "Birmingham, UK": (52.4862, -1.8904, 140.0),
    "Bristol, UK": (51.4545, -2.5879, 11.0),
    "Cardiff, UK": (51.4816, -3.1791, 9.0),
    "Coventry, UK": (52.4068, -1.5197, 90.0),
    "Dundee, UK": (56.4620, -2.9707, 15.0),
    "Edinburgh, UK": (55.9533, -3.1883, 47.0),
    "Glasgow, UK": (55.8642, -4.2518, 40.0),
    "Leeds, UK": (53.8008, -1.5491, 65.0),
    "Leicester, UK": (52.6369, -1.1398, 62.0),
    "Liverpool, UK": (53.4084, -2.9916, 70.0),
    "London, UK": (51.5074, -0.1278, 35.0),
    "Manchester, UK": (53.4808, -2.2426, 38.0),
    "Newcastle, UK": (54.9783, -1.6178, 45.0),
    "Nottingham, UK": (52.9548, -1.1581, 45.0),
    "Plymouth, UK": (50.3755, -4.1427, 15.0),
    "Sheffield, UK": (53.3811, -1.4701, 60.0),
    "Southampton, UK": (50.9097, -1.4044, 9.0),
    "Swansea, UK": (51.6214, -3.9436, 10.0),
    # ---- World ----
    "Auckland, New Zealand": (-36.8509, 174.7645, 20.0),
    "Beijing, China": (39.9042, 116.4074, 44.0),
    "Berlin, Germany": (52.5200, 13.4050, 34.0),
    "Buenos Aires, Argentina": (-34.6037, -58.3816, 25.0),
    "Cape Town, South Africa": (-33.9249, 18.4241, 25.0),
    "Delhi, India": (28.7041, 77.1025, 216.0),
    "Dubai, UAE": (25.2048, 55.2708, 16.0),
    "Lagos, Nigeria": (6.5244, 3.3792, 41.0),
    "Los Angeles, USA": (34.0522, -118.2437, 89.0),
    "Mexico City, Mexico": (19.4326, -99.1332, 2240.0),
    "Moscow, Russia": (55.7558, 37.6173, 156.0),
    "Mumbai, India": (19.0760, 72.8777, 14.0),
    "Nairobi, Kenya": (-1.2921, 36.8219, 1795.0),
    "New York, USA": (40.7128, -74.0060, 10.0),
    "Paris, France": (48.8566, 2.3522, 35.0),
    "Singapore": (1.3521, 103.8198, 15.0),
    "Sydney, Australia": (-33.8688, 151.2093, 58.0),
    "São Paulo, Brazil": (-23.5505, -46.6333, 760.0),
    "Tokyo, Japan": (35.6762, 139.6503, 40.0),
    "Toronto, Canada": (43.6532, -79.3832, 76.0),
    # ---- Custom ----
    "Custom (enter lat/lon)": None,
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