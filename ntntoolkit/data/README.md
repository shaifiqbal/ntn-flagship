# TLE snapshot

`starlink_snapshot.tle` is a recent real Starlink TLE set, served by the app when
a live Celestrak fetch is unavailable (e.g. the cloud host is rate-limited).

Refresh it with:

    python tools/refresh_snapshot.py

then commit the updated file. A GitHub Actions workflow can do this automatically.
