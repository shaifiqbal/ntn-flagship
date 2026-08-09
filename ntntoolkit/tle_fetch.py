"""
Fetch Starlink TLEs, newest-first fallback chain:

  1. live Celestrak                -> source "celestrak-live"
  2. a committed real snapshot     -> source "snapshot (YYYY-MM-DD)"
  3. the synthetic sample set      -> source "stored-sample"

Celestrak returns HTTP 403 without a browser-like User-Agent, so one is set.
The snapshot exists because cloud hosts (e.g. Streamlit Cloud) are often
rate-limited by Celestrak: the deployed app then serves recent REAL orbital data
instead of the synthetic sample. Refresh it with tools/refresh_snapshot.py.
"""

from __future__ import annotations

import os
import urllib.request

CELESTRAK_STARLINK_URL = (
    "https://celestrak.org/NORAD/elements/gp.php?GROUP=starlink&FORMAT=tle"
)
_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
)
_SNAPSHOT_PATH = os.path.join(os.path.dirname(__file__), "data", "starlink_snapshot.tle")


def fetch_starlink_tles(url: str = CELESTRAK_STARLINK_URL, timeout: float = 20.0):
    req = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        text = resp.read().decode("utf-8", "ignore")
    return parse_tle_text(text)


def parse_tle_text(text: str):
    lines = [ln.rstrip() for ln in text.splitlines()
             if ln.strip() and not ln.lstrip().startswith("#")]
    out = []
    i = 0
    while i + 2 <= len(lines):
        name, l1, l2 = lines[i], lines[i + 1], lines[i + 2]
        if l1.startswith("1 ") and l2.startswith("2 "):
            out.append((name.strip(), l1, l2))
            i += 3
        else:
            i += 1
    return out


def _load_snapshot():
    """Return ``(tles, date_str)`` from the committed snapshot, or ``(None, None)``.
    The snapshot's first line may be ``# snapshot: YYYY-MM-DD``."""
    if not os.path.exists(_SNAPSHOT_PATH):
        return None, None
    try:
        with open(_SNAPSHOT_PATH, "r", encoding="utf-8") as f:
            raw = f.read()
    except OSError:
        return None, None
    date_str = None
    first = raw.splitlines()[0] if raw.strip() else ""
    if first.startswith("# snapshot:"):
        date_str = first.split(":", 1)[1].strip()
    tles = parse_tle_text(raw)
    return (tles or None), date_str


def load_starlink_set(prefer_live: bool = True, limit: int = 60):
    """Return ``(tles, source)`` - a list of (name, l1, l2) and the source label."""
    if prefer_live:
        try:
            sats = fetch_starlink_tles()
            if sats:
                return sats[:limit], "celestrak-live"
        except Exception:
            pass

    snap, date_str = _load_snapshot()
    if snap:
        label = f"snapshot ({date_str})" if date_str else "snapshot"
        return snap[:limit], label

    from tests.sample_tle import SAMPLE_TLES
    return list(SAMPLE_TLES), "stored-sample"
