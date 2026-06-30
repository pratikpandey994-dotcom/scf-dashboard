# SCF Pod Dashboard on Streamlit

Hosts the existing single-file HTML dashboard **unchanged** inside Streamlit.
No logic, theme, or structure is rewritten — Streamlit only serves the HTML in
a full-width iframe. Chart.js, SheetJS file uploads, IndexedDB caching, the pod
selector, and all metrics run exactly as in the standalone file.

## Repo layout
```
scf-streamlit/
├── app.py                  # thin host wrapper (do not edit logic here)
├── requirements.txt
├── .streamlit/
│   └── config.toml         # enableStaticServing = true (required for storage)
└── static/
    └── dashboard.html      # <-- PUT YOUR CURRENT DASHBOARD HTML HERE
```

## Setup
1. Copy your current dashboard file in as `static/dashboard.html`
   (rename whatever the current version is, e.g. `scf_pod_dashboard_v3.html`).
2. Commit and push all files to a GitHub repo.

## Deploy on Streamlit Community Cloud
1. Go to https://share.streamlit.io and connect the GitHub repo.
2. Set the main file to `app.py`.
3. Deploy. Done.

## Run locally
```bash
pip install -r requirements.txt
streamlit run app.py
```

## Notes
- **Why a real static file, not srcdoc:** the dashboard caches the large
  historical OB file in IndexedDB. Embedded srcdoc iframes get a `null` origin
  and browsers block storage there. Serving via `static/` gives a real origin,
  so caching works.
- **Updating the dashboard:** replace `static/dashboard.html` and push. The new
  file supersedes the old one, same as the standalone workflow.
- **Iframe height:** the dashboard scrolls internally; `IFRAME_HEIGHT` in
  `app.py` sets the visible window. Adjust if you want a taller default frame.
