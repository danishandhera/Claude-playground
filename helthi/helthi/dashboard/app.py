"""Streamlit dashboard entrypoint -- FRONTEND OWNS THIS FILE.

Backend leaves this as a minimal placeholder so the package layout is complete.
Frontend builds the four insight tabs here, reading ONLY the unified layer (`day`,
`session`, `session_hr_zone`) and calling functions in `insights.py`. Do not read
raw tables or run ingest from the dashboard.

Contract to code against (all in helthi/insights.py, return list[dict]):
  IMPLEMENTED NOW (Whoop-only): daily_frame, recovery_trend, sleep_trend,
    strain_trend, long_term_trends
  STUBBED (return [] until later phases): recovery_vs_load, sleep_vs_performance,
    hr_zones_per_workout, strength_progression

Run: `streamlit run helthi/dashboard/app.py`
"""

from __future__ import annotations

import sys
from pathlib import Path

_PKG_DIR = str(Path(__file__).resolve().parent.parent)
if _PKG_DIR not in sys.path:
    sys.path.insert(0, _PKG_DIR)


def main() -> None:
    import streamlit as st  # imported here so non-dashboard use doesn't need it

    from config import load_config
    from db import connect
    import insights

    st.set_page_config(page_title="helthi", layout="wide")
    st.title("helthi")
    st.caption("Placeholder dashboard -- FRONTEND builds the four insight tabs here.")

    cfg = load_config()
    conn = connect(cfg.db_path)
    trends = insights.long_term_trends(conn)
    st.subheader("Long-term trends (insight #4, Whoop)")
    st.write({k: len(v) for k, v in trends.items()})
    st.dataframe(insights.daily_frame(conn))


if __name__ == "__main__":
    main()
