"""
Fetch live Starlink TLEs from Celestrak, with a graceful fallback to a stored
sample set offline. Celestrak returns HTTP 403 without a browser-like User-Agent,
so one is set explicitly.
"""

from __future__ import annotations

import urllib.request

CELESTRAK_STARLINK_URL = (
    "https://celestrak.org/NORAD/elements/gp.php?GROUP=starlink&FORMAT=tle"
)
_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
)


def fetch_starlink_tles(url: str = CELESTRAK_STARLINK_URL, timeout: float = 20.0):
    req = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        text = resp.read().decode("utf-8", "ignore")
    return parse_tle_text(text)


def parse_tle_text(text: str):
    lines = [ln.rstrip() for ln in text.splitlines() if ln.strip()]
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


def load_starlink_set(prefer_live: bool = True, limit: int = 60):
    """Return ``(tles, source)`` - a list of (name, l1, l2) and the source used."""
    if prefer_live:
        try:
            sats = fetch_starlink_tles()
            if sats:
                return sats[:limit], "celestrak-live"
        except Exception:
            pass
    from tests.sample_tle import SAMPLE_TLES

    return list(SAMPLE_TLES), "stored-sample"
