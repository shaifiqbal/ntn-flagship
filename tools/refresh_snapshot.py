"""
Refresh the bundled Starlink TLE snapshot from live Celestrak.

Run this from a machine/network that can reach Celestrak (i.e. NOT the Streamlit
cloud host). It writes a dated real-TLE file that the deployed app serves whenever
its own live fetch is rate-limited, so users see recent REAL orbital data.

    python tools/refresh_snapshot.py

Then commit the updated file:

    git add ntntoolkit/data/starlink_snapshot.tle
    git commit -m "Refresh Starlink TLE snapshot"
    git push
"""

from __future__ import annotations

import datetime as _dt
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ntntoolkit.tle_fetch import fetch_starlink_tles, _SNAPSHOT_PATH

MAX_SATS = 120  # plenty for the app; keeps the file small


def main() -> None:
    print("Fetching live Starlink TLEs from Celestrak ...")
    try:
        tles = fetch_starlink_tles()
    except Exception as e:  # noqa: BLE001
        print(f"  FAILED: {e}")
        print("  Try again, or use a phone hotspot / different network.")
        sys.exit(1)

    if not tles:
        print("  No TLEs returned - aborting.")
        sys.exit(1)

    tles = tles[:MAX_SATS]
    today = _dt.date.today().isoformat()
    os.makedirs(os.path.dirname(_SNAPSHOT_PATH), exist_ok=True)
    with open(_SNAPSHOT_PATH, "w", encoding="utf-8") as f:
        f.write(f"# snapshot: {today}\n")
        f.write(f"# source: celestrak.org GROUP=starlink  ({len(tles)} satellites)\n")
        for name, l1, l2 in tles:
            f.write(f"{name}\n{l1}\n{l2}\n")

    print(f"  OK - wrote {len(tles)} satellites to {_SNAPSHOT_PATH}")
    print(f"  dated {today}")
    print("\nNow commit it:")
    print("  git add ntntoolkit/data/starlink_snapshot.tle")
    print('  git commit -m "Refresh Starlink TLE snapshot"')
    print("  git push")


if __name__ == "__main__":
    main()
