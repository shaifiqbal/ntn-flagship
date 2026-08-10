"""
Refresh the bundled Starlink TLE snapshot from live Celestrak.

Self-contained (standard library only) so it runs anywhere - locally, or in a
GitHub Actions runner - without installing the app's scientific dependencies.

It writes a dated real-TLE file that the deployed app serves whenever its own
live fetch is rate-limited, so users see recent REAL orbital data.

    python tools/refresh_snapshot.py

Locally, then commit the updated file:

    git add ntntoolkit/data/starlink_snapshot.tle
    git commit -m "Refresh Starlink TLE snapshot"
    git push

In CI, the workflow commits it automatically (see .github/workflows/).
"""

from __future__ import annotations

import datetime as _dt
import os
import sys
import urllib.request

CELESTRAK_STARLINK_URL = (
    "https://celestrak.org/NORAD/elements/gp.php?GROUP=starlink&FORMAT=tle"
)
_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
)
_SNAPSHOT_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "ntntoolkit", "data", "starlink_snapshot.tle",
)
MAX_SATS = 120  # plenty for the app; keeps the file small


def _fetch(url: str = CELESTRAK_STARLINK_URL, timeout: float = 30.0) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", "ignore")


def _parse(text: str):
    lines = [ln.rstrip() for ln in text.splitlines()
             if ln.strip() and not ln.lstrip().startswith("#")]
    out, i = [], 0
    while i + 2 <= len(lines):
        name, l1, l2 = lines[i], lines[i + 1], lines[i + 2]
        if l1.startswith("1 ") and l2.startswith("2 "):
            out.append((name.strip(), l1, l2))
            i += 3
        else:
            i += 1
    return out


def main() -> None:
    print("Fetching live Starlink TLEs from Celestrak ...")
    try:
        text = _fetch()
    except Exception as e:  # noqa: BLE001
        print(f"  FAILED: {e}")
        print("  (locally: try a phone hotspot / different network)")
        sys.exit(1)

    tles = _parse(text)[:MAX_SATS]
    if not tles:
        print("  No TLEs parsed - aborting.")
        sys.exit(1)

    today = _dt.date.today().isoformat()
    os.makedirs(os.path.dirname(_SNAPSHOT_PATH), exist_ok=True)
    with open(_SNAPSHOT_PATH, "w", encoding="utf-8") as f:
        f.write(f"# snapshot: {today}\n")
        f.write(f"# source: celestrak.org GROUP=starlink  ({len(tles)} satellites)\n")
        for name, l1, l2 in tles:
            f.write(f"{name}\n{l1}\n{l2}\n")

    print(f"  OK - wrote {len(tles)} satellites to {_SNAPSHOT_PATH}")
    print(f"  dated {today}")


if __name__ == "__main__":
    main()