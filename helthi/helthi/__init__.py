"""helthi -- local fitness-data consolidator (Whoop + Hevy + Samsung -> SQLite).

Package layout (ARCHITECTURE.md §2). Backend owns db/schema, parsers, unify,
time_align, insights; Frontend owns dashboard/app.py (Streamlit) and reads only
the unified layer + insights.py.
"""

__version__ = "0.1.0"
