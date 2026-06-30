"""
SCF Pod Dashboard — Streamlit host wrapper.

This does NOT reimplement the dashboard. It serves the existing single-file
HTML (static/dashboard.html) inside a full-width iframe so that every line of
the original HTML/CSS/JS — Chart.js charts, SheetJS uploads, IndexedDB caching,
the Slate & Amber theme, pod selector, and all logic — runs unchanged.

The HTML is served as a real static file (not srcdoc) so the iframe keeps a
real same-origin URL. This is required for IndexedDB / localStorage to work,
which the dashboard depends on for caching the historical OB file.
"""

import os
import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(
    page_title="SCF Pod Dashboard",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Strip Streamlit chrome so the dashboard fills the page edge-to-edge.
st.markdown(
    """
    <style>
      .block-container { padding: 0 !important; max-width: 100% !important; }
      header[data-testid="stHeader"] { display: none; }
      footer { display: none; }
      #MainMenu { visibility: hidden; }
      [data-testid="stAppViewBlockContainer"] { padding: 0 !important; }
      html, body { background: #1a1a2e; }
    </style>
    """,
    unsafe_allow_html=True,
)

DASHBOARD_PATH = os.path.join("static", "dashboard.html")

# Auto-sync data from Google Drive and Sheets on startup/refresh
try:
    import data_sync
    with st.spinner("Syncing latest data from Google Drive & Sheets..."):
        data_sync.run_syncs()
except Exception as e:
    st.error(f"Failed to sync data: {e}")

if not os.path.exists(DASHBOARD_PATH):
    st.error(
        "static/dashboard.html not found.\n\n"
        "Place your current dashboard HTML file at `static/dashboard.html` "
        "in the repo, then redeploy."
    )
    st.stop()

# Served via Streamlit static serving (enableStaticServing = true in config.toml).
# Files in static/ are exposed at the /app/static/ URL path, giving the iframe a
# real origin so IndexedDB / localStorage work.
#
# IFRAME_HEIGHT: the dashboard scrolls internally, so a generous fixed height
# plus scrolling=True is the simplest reliable approach. Tune to taste.
IFRAME_HEIGHT = 2600

components.iframe("app/static/dashboard.html", height=IFRAME_HEIGHT, scrolling=True)
