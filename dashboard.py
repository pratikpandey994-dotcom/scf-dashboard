"""CP Pod · SCF Portfolio Dashboard — Streamlit Cloud edition"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import date, datetime, timedelta
import calendar
import io

st.set_page_config(
    page_title="CP Pod · SCF Portfolio",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ══════════════════════════════════════════════════════════════════════════════
# DESIGN SYSTEM
# ══════════════════════════════════════════════════════════════════════════════
THEME_CSS = """
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600&family=IBM+Plex+Sans:wght@300;400;500;600;700&display=swap" rel="stylesheet">
<style>
/* ── Tokens ───────────────────────────────────────────────── */
:root{
  --bg:#0d1117; --bg-card:#161b22; --bg-hover:#1c2430; --bg-input:#0d1117;
  --border:#21262d; --border-hi:#30363d;
  --amber:#f59e0b; --green:#10b981; --red:#ef4444; --orange:#f97316; --blue:#6366f1;
  --t1:#e6edf3; --t2:#8b949e; --t3:#484f58;
  --mono:'IBM Plex Mono',monospace; --sans:'IBM Plex Sans',sans-serif; --r:6px;
}

/* ── Base ─────────────────────────────────────────────────── */
html,body{background:var(--bg)!important;font-family:var(--sans)!important;color:var(--t1)!important}
.stApp{background:var(--bg)!important}
.stApp > header{background:transparent!important;border-bottom:none!important}
section[data-testid="stSidebar"]{background:var(--bg-card)!important;border-right:1px solid var(--border)!important}
.block-container{padding:1.2rem 2rem 3rem!important;max-width:1560px!important}
/* Streamlit 1.57 wraps content in stMainBlockContainer */
[data-testid="stMainBlockContainer"]{padding:1.2rem 2rem 3rem!important;max-width:1560px!important}
p,span,div,label{font-family:var(--sans)!important}
h1,h2,h3{font-family:var(--sans)!important;color:var(--t1)!important}
a{color:var(--amber)!important}

/* ── Tabs ─────────────────────────────────────────────────── */
[data-testid="stTabs"] [role="tablist"]{
  background:var(--bg-card);border:1px solid var(--border);
  border-radius:var(--r);padding:3px;gap:2px;flex-wrap:wrap
}
[data-testid="stTabs"] button[role="tab"]{
  font-family:var(--sans)!important;font-size:.7rem!important;
  font-weight:600!important;letter-spacing:.04em;
  color:var(--t2)!important;border-radius:4px!important;
  padding:5px 12px!important;border:none!important;
  background:transparent!important;transition:all .15s;white-space:nowrap
}
[data-testid="stTabs"] button[role="tab"]:hover{
  color:var(--t1)!important;background:var(--bg-hover)!important
}
[data-testid="stTabs"] button[role="tab"][aria-selected="true"]{
  background:var(--amber)!important;color:#0d1117!important
}
[data-testid="stTabs"] [role="tabpanel"]{padding-top:1.2rem!important}
/* Hide Streamlit's default tab underline */
[data-testid="stTabs"] [role="tablist"]::after{display:none!important}
[data-testid="stTabs"] button[role="tab"] p{
  font-family:var(--sans)!important;font-size:.7rem!important;font-weight:600!important
}

/* ── st.metric ────────────────────────────────────────────── */
[data-testid="stMetric"]{
  background:var(--bg-card);border:1px solid var(--border);
  border-radius:var(--r);padding:14px 16px!important
}
[data-testid="stMetricLabel"] p,
[data-testid="stMetricLabel"] > div > div{
  font-family:var(--sans)!important;font-size:.62rem!important;
  font-weight:700!important;letter-spacing:.09em;
  text-transform:uppercase;color:var(--t2)!important
}
[data-testid="stMetricValue"] > div{
  font-family:var(--mono)!important;font-size:1.35rem!important;
  font-weight:600!important;color:var(--amber)!important;line-height:1.2
}
[data-testid="stMetricDelta"] svg{display:none!important}
[data-testid="stMetricDelta"] > div{
  font-family:var(--mono)!important;font-size:.68rem!important;color:var(--t3)!important
}

/* ── Dataframe ────────────────────────────────────────────── */
[data-testid="stDataFrame"]{
  border:1px solid var(--border)!important;border-radius:var(--r)!important;overflow:hidden
}
[data-testid="stDataFrame"] iframe,
.stDataFrame iframe{background:var(--bg-card)!important}

/* ── Selectbox ────────────────────────────────────────────── */
[data-testid="stSelectbox"] > div > div{
  background:var(--bg-card)!important;border:1px solid var(--border)!important;
  border-radius:var(--r)!important;color:var(--t1)!important
}
[data-testid="stSelectbox"] svg{color:var(--t2)!important}

/* ── Number input ─────────────────────────────────────────── */
[data-testid="stNumberInput"] > div{
  background:var(--bg-card)!important;border:1px solid var(--border)!important;border-radius:var(--r)!important
}
[data-testid="stNumberInput"] input{background:transparent!important;color:var(--t1)!important;font-family:var(--mono)!important}

/* ── Radio ────────────────────────────────────────────────── */
[data-testid="stRadio"] > label{
  font-family:var(--sans)!important;font-size:.62rem!important;
  font-weight:700!important;letter-spacing:.07em;text-transform:uppercase;color:var(--t3)!important
}
[data-testid="stRadio"] div[role="radiogroup"]{gap:4px!important}
[data-testid="stRadio"] label[data-baseweb="radio"] span:first-child{
  background:var(--bg-card)!important;border-color:var(--border-hi)!important
}
[data-testid="stRadio"] label[data-baseweb="radio"][aria-checked="true"] span:first-child{
  border-color:var(--amber)!important;background:var(--amber)!important
}
[data-testid="stRadio"] label[data-baseweb="radio"] div{
  font-family:var(--sans)!important;font-size:.75rem!important;color:var(--t2)!important
}
[data-testid="stRadio"] label[data-baseweb="radio"][aria-checked="true"] div{color:var(--amber)!important}

/* ── Buttons ──────────────────────────────────────────────── */
button[data-testid="stBaseButton-secondary"]{
  font-family:var(--sans)!important;font-weight:600!important;font-size:.74rem!important;
  letter-spacing:.04em;border-radius:var(--r)!important;transition:all .15s!important;
  border:1px solid var(--border)!important;background:var(--bg-card)!important;color:var(--t2)!important
}
button[data-testid="stBaseButton-secondary"]:hover{
  border-color:var(--amber)!important;color:var(--amber)!important;background:var(--bg-hover)!important
}
button[data-testid="stBaseButton-primary"]{
  font-family:var(--sans)!important;font-weight:700!important;font-size:.78rem!important;
  letter-spacing:.04em;border-radius:var(--r)!important;
  background:var(--amber)!important;border-color:var(--amber)!important;color:#0d1117!important
}
button[data-testid="stBaseButton-primary"]:hover{background:#fbbf24!important;border-color:#fbbf24!important}
button[data-testid="stBaseButton-primary"]:disabled{background:var(--t3)!important;border-color:var(--t3)!important;color:#0d1117!important;cursor:not-allowed!important}

/* ── Expander ─────────────────────────────────────────────── */
[data-testid="stExpander"]{
  background:var(--bg-card)!important;border:1px solid var(--border)!important;
  border-radius:var(--r)!important;margin-bottom:6px!important
}
[data-testid="stExpander"] details summary{
  font-family:var(--sans)!important;font-size:.74rem!important;
  font-weight:600!important;color:var(--t2)!important;padding:10px 14px!important
}
[data-testid="stExpander"] details summary:hover{
  color:var(--t1)!important;background:rgba(255,255,255,.03)!important
}
[data-testid="stExpander"] details[open] summary{color:var(--t1)!important}
[data-testid="stExpanderDetails"]{padding:2px 14px 12px!important}

/* ── File uploader ────────────────────────────────────────── */
[data-testid="stFileUploaderDropzone"]{
  background:var(--bg-card)!important;border:1.5px dashed var(--border-hi)!important;
  border-radius:var(--r)!important;transition:border-color .2s!important
}
[data-testid="stFileUploaderDropzone"]:hover{border-color:var(--amber)!important}
[data-testid="stFileUploaderDropzone"] > div{padding:12px!important}
[data-testid="stFileUploaderDropzone"] span{font-family:var(--sans)!important;font-size:.76rem!important;color:var(--t2)!important}
[data-testid="stFileUploaderDropzone"] small{font-size:.62rem!important;color:var(--t3)!important}
[data-testid="stFileUploader"] label p{
  font-family:var(--sans)!important;font-size:.68rem!important;
  font-weight:700!important;letter-spacing:.08em;text-transform:uppercase;color:var(--t2)!important
}
/* Uploaded file chip */
[data-testid="stFileUploader"] [data-testid="stFileUploadDeleteBtn"]{color:var(--red)!important}
[data-testid="stUploadedFile"]{background:var(--bg-hover)!important;border:1px solid var(--border)!important;border-radius:4px!important}
[data-testid="stUploadedFileName"]{color:var(--green)!important;font-family:var(--mono)!important;font-size:.72rem!important}

/* ── Date input ───────────────────────────────────────────── */
[data-testid="stDateInput"] input{
  background:var(--bg-card)!important;border:1px solid var(--border)!important;
  border-radius:var(--r)!important;color:var(--amber)!important;font-family:var(--mono)!important;font-size:.85rem!important
}
[data-testid="stDateInput"] label p{
  font-family:var(--sans)!important;font-size:.68rem!important;
  font-weight:700!important;letter-spacing:.08em;text-transform:uppercase;color:var(--t2)!important
}

/* ── Alerts ───────────────────────────────────────────────── */
[data-testid="stAlert"]{border-radius:var(--r)!important;font-size:.8rem!important;font-family:var(--sans)!important}

/* ── Divider ──────────────────────────────────────────────── */
[data-testid="stMarkdown"] hr{border:none!important;border-top:1px solid var(--border)!important;margin:.8rem 0!important}

/* ── Spinner ──────────────────────────────────────────────── */
[data-testid="stSpinner"] > div{border-top-color:var(--amber)!important}

/* ── Scrollbar ────────────────────────────────────────────── */
::-webkit-scrollbar{width:5px;height:5px}
::-webkit-scrollbar-track{background:var(--bg)}
::-webkit-scrollbar-thumb{background:var(--border-hi);border-radius:3px}
::-webkit-scrollbar-thumb:hover{background:var(--t3)}
</style>
"""

# ── Plotly base layout (reuse across all charts) ─────────────
def plotly_layout(**kwargs):
    base = dict(
        paper_bgcolor="#161b22", plot_bgcolor="#161b22",
        font=dict(family="IBM Plex Sans", color="#8b949e", size=11),
        margin=dict(l=8, r=8, t=28, b=8),
        legend=dict(bgcolor="rgba(0,0,0,0)", bordercolor="rgba(0,0,0,0)",
                    font=dict(size=11, color="#8b949e")),
        xaxis=dict(gridcolor="rgba(33,38,45,.6)", zeroline=False,
                   tickfont=dict(family="IBM Plex Mono", size=10)),
        yaxis=dict(gridcolor="rgba(33,38,45,.6)", zeroline=False,
                   tickfont=dict(family="IBM Plex Mono", size=10)),
    )
    base.update(kwargs)
    return base

# ── HTML component helpers ────────────────────────────────────
def kpi_card(label, value, sub="", color="amber", border=True):
    c = {"amber":"#f59e0b","green":"#10b981","red":"#ef4444","orange":"#f97316","muted":"#484f58"}[color]
    bc = f"border-left:3px solid {c};" if border else ""
    return f"""<div style="background:#161b22;border:1px solid #21262d;{bc}border-radius:6px;padding:14px 16px;height:100%">
  <div style="font-family:'IBM Plex Sans',sans-serif;font-size:.6rem;font-weight:700;letter-spacing:.1em;text-transform:uppercase;color:#8b949e;margin-bottom:6px">{label}</div>
  <div style="font-family:'IBM Plex Mono',monospace;font-size:1.45rem;font-weight:600;color:{c};line-height:1.1">{value}</div>
  {"" if not sub else f'<div style="font-family:IBM Plex Mono,monospace;font-size:.68rem;color:#484f58;margin-top:4px">{sub}</div>'}
</div>"""

def badge(text, variant="default"):
    styles = {
        "active":    "background:rgba(16,185,129,.12);color:#10b981;border:1px solid rgba(16,185,129,.25)",
        "suspended": "background:rgba(249,115,22,.12);color:#f97316;border:1px solid rgba(249,115,22,.25)",
        "npa":       "background:rgba(239,68,68,.12);color:#ef4444;border:1px solid rgba(239,68,68,.25)",
        "overdue":   "background:rgba(249,115,22,.12);color:#f97316;border:1px solid rgba(249,115,22,.25)",
        "clean":     "background:rgba(16,185,129,.10);color:#10b981;border:1px solid rgba(16,185,129,.2)",
        "target":    "background:rgba(245,158,11,.12);color:#f59e0b;border:1px solid rgba(245,158,11,.25)",
        "nwa":       "background:rgba(72,79,88,.2);color:#484f58;border:1px solid rgba(72,79,88,.3)",
        "default":   "background:rgba(139,148,158,.1);color:#8b949e;border:1px solid rgba(139,148,158,.2)",
    }
    s = styles.get(variant, styles["default"])
    return f'<span style="display:inline-block;{s};border-radius:10px;font-family:IBM Plex Sans,sans-serif;font-size:.6rem;font-weight:700;letter-spacing:.06em;text-transform:uppercase;padding:2px 8px;white-space:nowrap">{text}</span>'

def section_header(title, subtitle="", right=""):
    sub_html = f'<span style="font-size:.72rem;color:#484f58;font-weight:400;margin-left:10px">{subtitle}</span>' if subtitle else ""
    right_html = f'<span style="font-size:.68rem;color:#484f58">{right}</span>' if right else ""
    return f"""<div style="display:flex;align-items:baseline;justify-content:space-between;margin:1.4rem 0 .8rem;padding-bottom:.5rem;border-bottom:1px solid #21262d">
  <div><span style="font-family:'IBM Plex Sans',sans-serif;font-size:.65rem;font-weight:700;letter-spacing:.12em;text-transform:uppercase;color:#8b949e">{title}</span>{sub_html}</div>
  {right_html}
</div>"""

def stat_row(items):
    """Horizontal row of small labeled stats."""
    cells = "".join(
        f'<div style="display:flex;flex-direction:column;gap:2px;min-width:80px">'
        f'<span style="font-family:IBM Plex Sans;font-size:.6rem;font-weight:600;letter-spacing:.08em;text-transform:uppercase;color:#484f58">{lbl}</span>'
        f'<span style="font-family:IBM Plex Mono;font-size:.85rem;font-weight:600;color:{col}">{val}</span></div>'
        for lbl, val, col in items
    )
    return f'<div style="display:flex;gap:20px;flex-wrap:wrap;background:#161b22;border:1px solid #21262d;border-radius:6px;padding:12px 16px;margin-bottom:8px">{cells}</div>'

def am_scorecard(name, initials, color, metrics):
    """AM card with avatar + metrics."""
    rows = "".join(
        f'<div style="display:flex;justify-content:space-between;padding:5px 0;border-bottom:1px solid #21262d">'
        f'<span style="font-family:IBM Plex Sans;font-size:.72rem;color:#8b949e">{lbl}</span>'
        f'<span style="font-family:IBM Plex Mono;font-size:.78rem;font-weight:600;color:{clr}">{val}</span></div>'
        for lbl, val, clr in metrics
    )
    return f"""<div style="background:#161b22;border:1px solid #21262d;border-top:2px solid {color};border-radius:6px;overflow:hidden">
  <div style="display:flex;align-items:center;gap:10px;padding:12px 14px;background:rgba(255,255,255,.02)">
    <div style="width:32px;height:32px;border-radius:50%;background:{color};color:#0d1117;display:flex;align-items:center;justify-content:center;font-family:IBM Plex Mono;font-weight:700;font-size:.75rem;flex-shrink:0">{initials}</div>
    <div style="font-family:IBM Plex Sans;font-weight:600;font-size:.88rem;color:#e6edf3">{name}</div>
  </div>
  <div style="padding:10px 14px">{rows}</div>
</div>"""

def info_banner(text, variant="info"):
    colors = {"info": ("#6366f1","rgba(99,102,241,.1)"), "warn": ("#f97316","rgba(249,115,22,.1)"), "tip": ("#f59e0b","rgba(245,158,11,.1)")}
    c, bg = colors.get(variant, colors["info"])
    return f'<div style="background:{bg};border:1px solid {c}40;border-radius:6px;padding:10px 14px;font-size:.76rem;color:{c};margin:8px 0">{text}</div>'

# ══════════════════════════════════════════════════════════════════════════════
# CONSTANTS
# ══════════════════════════════════════════════════════════════════════════════
POD_AMS   = ["Nikhil Shetty","Darshan Hublikar","Deepsayan Dam","Ashitha Nair","Asif Ali"]
AM_COLORS = ["#f59e0b","#10b981","#6366f1","#f97316","#94a3b8"]
AM_INIT   = {"Nikhil Shetty":"NS","Darshan Hublikar":"DH","Deepsayan Dam":"DD",
             "Ashitha Nair":"AN","Asif Ali":"AA"}
SETTLED   = {"closed","paid","received"}
OPEN_ST   = {"advanced","overdue","npa","partial"}
EXCL_ST   = {"partadvanced","processing","deposit_pending","pending_advance",
             "data_entry","verify_bank_details","hold"}
OB_CUTOFF = pd.Timestamp("2026-05-01")

# ══════════════════════════════════════════════════════════════════════════════
# DATA HELPERS
# ══════════════════════════════════════════════════════════════════════════════
def norm_id(v):
    if pd.isna(v): return ""
    s = str(v).replace(",","").strip()
    return s[:-2] if s.endswith(".0") else s

def fmt_ccy(v, short=True):
    if v is None or (isinstance(v, float) and np.isnan(v)): return "—"
    v = float(v); a = abs(v)
    if short:
        if a >= 1e6: return f"${v/1e6:.2f}M"
        if a >= 1e3: return f"${v/1e3:.1f}K"
        return f"${v:.0f}"
    return f"${v:,.0f}"

def fmt_pct(v):
    if v is None or (isinstance(v, float) and np.isnan(v)): return "—"
    return f"{float(v)*100:.1f}%"

def fmt_irr(v):
    if not v or (isinstance(v, float) and (np.isnan(v) or v == 0)): return "—"
    return f"{float(v):.2f}%"

def fmt_date(d):
    if d is None or (isinstance(d, float) and np.isnan(d)): return "—"
    try: return pd.Timestamp(d).strftime("%d %b %Y")
    except: return "—"

def wirr(df, ob_col="ob", irr_col="irr", thresh=0):
    s = df[df[ob_col] >= thresh] if thresh > 0 else df
    tot = s[ob_col].sum()
    return (s[irr_col] * s[ob_col]).sum() / tot if tot > 0 else None

def get_window(win, today_ts):
    t = pd.Timestamp(today_ts); y, m = t.year, t.month; dow = t.weekday()
    if win == "mtd":  return pd.Timestamp(y, m, 1), t
    if win == "qtd":  return pd.Timestamp(y, (m-1)//3*3+1, 1), t
    if win == "cw":   s = t - timedelta(days=dow); return s, s + timedelta(days=6)
    if win == "nw":   s = t - timedelta(days=dow) + timedelta(weeks=1); return s, s + timedelta(days=6)
    if win == "cm":   return pd.Timestamp(y, m, 1), pd.Timestamp(y, m, calendar.monthrange(y, m)[1])
    if win == "nm":
        nm = m+1 if m < 12 else 1; ny = y if m < 12 else y+1
        return pd.Timestamp(ny, nm, 1), pd.Timestamp(ny, nm, calendar.monthrange(ny, nm)[1])
    if win == "wtd":  return t - timedelta(days=dow), t
    return pd.Timestamp(y, m, 1), t

def in_win(d, s, e):
    if d is None or (isinstance(d, float) and np.isnan(d)): return False
    try: d = pd.Timestamp(d); return s <= d <= e
    except: return False

def closest_before(target, keys):
    best = None
    for k in keys:
        if str(k) <= str(target): best = k
    return best

# ══════════════════════════════════════════════════════════════════════════════
# FILE LOADERS
# ══════════════════════════════════════════════════════════════════════════════
def read_excel(uploaded):
    uploaded.seek(0)
    return pd.read_excel(io.BytesIO(uploaded.read()))

def load_v1(uploaded):
    df = read_excel(uploaded)
    df["importer_user_id"] = df["importer_user_id"].apply(norm_id)
    for c in ["Facility_Size","Outstanding_Balance","overdraft_limit","Signed-up IRR"]:
        df[c] = pd.to_numeric(df[c] if c in df.columns else 0, errors="coerce").fillna(0)
    df["First_Disbursed_Date"] = pd.to_datetime(df["First_Disbursed_Date"], errors="coerce")
    df["Last_Disbursed_Date"]  = pd.to_datetime(df["Last_Disbursed_Date"],  errors="coerce")
    df["AM_Name"] = df["AM_Name"].astype(str).str.strip()
    df["utilization_status"] = df["utilization_status"].astype(str).str.strip().str.lower()
    return df.set_index("importer_user_id")

def load_v2(uploaded):
    df = read_excel(uploaded)
    df["Buyer"] = df["Buyer"].astype(str).str.strip()
    df["buyer_lower"] = df["Buyer"].str.lower()
    df["Stage"] = df["Stage"].astype(str).str.strip().str.lower()
    for c in ["Origination","Outstanding","dpd"]:
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)
    for c in ["disbursed_date","settlement_date","due_date_of_invoice"]:
        df[c] = pd.to_datetime(df[c], errors="coerce")
    return df

def load_mh(uploaded):
    df = read_excel(uploaded)
    df["Buyer_ID"] = df["Buyer_ID"].apply(norm_id)
    df["Buyer"] = df["Buyer"].astype(str).str.strip()
    df["AM"]    = df["AM"].astype(str).str.strip()
    for c in ["Broad_Account_Status","Account_Status","Team"]:
        df[c] = df[c].astype(str).str.strip()
    df["Partner"] = (df["Partner"] if "Partner" in df.columns else pd.Series([""], index=df.index)).astype(str).str.strip()
    for c in ["Facility_Size","Overdraft_Limit","OB","Signed_up_IRR"]:
        df[c] = pd.to_numeric(df[c] if c in df.columns else 0, errors="coerce").fillna(0)
    df["First_Disbursed_Date"] = pd.to_datetime(df["First_Disbursed_Date"], errors="coerce")
    df["Last_Disbursed_Date"]  = pd.to_datetime(df["Last_Disbursed_Date"],  errors="coerce")
    return df

def load_ob(uploaded, filter_fn):
    df = read_excel(uploaded)
    df["importer_user_id"] = df["importer_user_id"].apply(norm_id)
    df["ob_date"] = pd.to_datetime(df["ob_date"], errors="coerce")
    df["ob"] = pd.to_numeric(df["ob"], errors="coerce").fillna(0)
    return df[df["ob_date"].apply(filter_fn)].dropna(subset=["ob_date"])

def process_data(v1, mh, v2, obhist, obcurr, today_ts):
    records = []
    for _, row in mh.iterrows():
        bid = row["Buyer_ID"]
        v1r = v1.loc[bid] if bid in v1.index else pd.Series(dtype=object)
        am  = str(v1r.get("AM_Name","") or "").strip() or str(row["AM"]).strip()
        if am not in POD_AMS: continue
        broad = row["Broad_Account_Status"]; v1u = str(v1r.get("utilization_status","") or "").strip().lower()
        ld = v1r.get("Last_Disbursed_Date") or row["Last_Disbursed_Date"]
        fd = v1r.get("First_Disbursed_Date") or row["First_Disbursed_Date"]
        ld = pd.Timestamp(ld) if pd.notna(ld) else pd.NaT
        fd = pd.Timestamp(fd) if pd.notna(fd) else pd.NaT
        ds = int((today_ts - ld).days) if pd.notna(ld) else None
        if   broad != "Workable":        l2 = "NWA"
        elif ds is None or ds > 365:     l2 = "Workable_Over365"
        elif v1u == "active":            l2 = "Active Workable"
        else:                            l2 = "Suspended Workable"
        fac = float(v1r.get("Facility_Size",0) or row["Facility_Size"] or 0)
        ovd = float(v1r.get("overdraft_limit",0) or row["Overdraft_Limit"] or 0)
        ob_v = v1r.get("Outstanding_Balance"); ob = float(ob_v if pd.notna(ob_v) else row["OB"] or 0)
        irr  = float(v1r.get("Signed-up IRR",0) or row["Signed_up_IRR"] or 0)
        records.append(dict(id=bid, company=row["Buyer"], am=am, broad=broad, level2=l2,
            v1_util=v1u, facility=fac, overdraft=ovd, total_fac=fac+ovd, ob=ob, irr=irr,
            first_disb=fd, last_disb=ld, days_since=ds,
            acct_status=row["Account_Status"], team=row["Team"]))

    pod = pd.DataFrame(records)
    pod_cos = set(pod["company"].str.lower())
    co_am   = dict(zip(pod["company"].str.lower(), pod["am"]))
    co_l2   = dict(zip(pod["company"].str.lower(), pod["level2"]))
    v2p = v2[v2["buyer_lower"].isin(pod_cos)].copy()
    v2p["am"]     = v2p["buyer_lower"].map(co_am).fillna("")
    v2p["level2"] = v2p["buyer_lower"].map(co_l2).fillna("")

    ob_pivot = pd.DataFrame()
    if obhist is not None or obcurr is not None:
        parts = [x for x in [obhist, obcurr] if x is not None]
        ob_all = pd.concat(parts)
        ob_all = ob_all[ob_all["importer_user_id"].isin(set(pod["id"]))].copy()
        ob_all["date_key"] = ob_all["ob_date"].dt.date
        ob_pivot = ob_all.groupby(["date_key","importer_user_id"])["ob"].last().unstack(fill_value=0)

    if not ob_pivot.empty:
        pod["peak_ob"]      = pod["id"].map(ob_pivot.max(axis=0)).fillna(0)
        pod["avg_ob"]       = pod["id"].map(ob_pivot.replace(0, np.nan).mean(axis=0)).fillna(0)
        pod["peak_ob_date"] = pod["id"].map(ob_pivot.idxmax(axis=0))
    else:
        pod["peak_ob"] = 0; pod["avg_ob"] = 0; pod["peak_ob_date"] = pd.NaT
    return pod, v2p, ob_pivot

# ══════════════════════════════════════════════════════════════════════════════
# INJECT THEME
# ══════════════════════════════════════════════════════════════════════════════
st.markdown(THEME_CSS, unsafe_allow_html=True)
ss = st.session_state

# ══════════════════════════════════════════════════════════════════════════════
# UPLOAD SCREEN
# ══════════════════════════════════════════════════════════════════════════════
def _file_status_html(checks):
    rows = ""
    for name, loaded, required in checks:
        if loaded:
            icon, ic, lc, tag = "✓", "#10b981", "#e6edf3", ""
        elif required:
            icon, ic, lc, tag = "○", "#f59e0b", "#8b949e", ' <span style="font-size:.6rem;color:#484f58;font-style:italic">required</span>'
        else:
            icon, ic, lc, tag = "○", "#30363d", "#484f58", ""
        rows += f"""<div style="display:flex;align-items:center;gap:10px;padding:7px 12px;border-bottom:1px solid #21262d">
          <span style="font-family:'IBM Plex Mono',monospace;font-weight:700;color:{ic};font-size:.8rem;width:14px;text-align:center">{icon}</span>
          <span style="font-family:'IBM Plex Sans',sans-serif;font-size:.76rem;color:{lc}">{name}{tag}</span>
        </div>"""
    return f'<div style="background:#161b22;border:1px solid #21262d;border-radius:6px;overflow:hidden">{rows}</div>'

def show_upload():
    # ── Header ──
    st.markdown("""
    <div style="padding:2rem 0 1.5rem">
      <div style="display:flex;align-items:center;gap:12px;margin-bottom:8px">
        <div style="width:40px;height:40px;background:#f59e0b;border-radius:8px;display:flex;align-items:center;justify-content:center;font-size:1.2rem;flex-shrink:0">📊</div>
        <div>
          <div style="font-family:'IBM Plex Sans',sans-serif;font-size:1.5rem;font-weight:700;color:#e6edf3;line-height:1.1">
            CP POD <span style="color:#f59e0b">·</span> SCF Portfolio
          </div>
          <div style="font-family:'IBM Plex Mono',monospace;font-size:.65rem;color:#484f58;letter-spacing:.1em;text-transform:uppercase;margin-top:3px">
            Supply Chain Finance Intelligence Platform
          </div>
        </div>
      </div>
      <div style="height:1px;background:linear-gradient(90deg,#f59e0b40,#21262d);margin:1rem 0"></div>
      <p style="font-family:'IBM Plex Sans',sans-serif;font-size:.82rem;color:#8b949e;margin:0">
        Upload your weekly Excel files below, set today's date, then click <strong style="color:#e6edf3">Launch Dashboard</strong>.
        Required files: View 1, View 2, Master Handover. Historical &amp; Current OB unlock the Peak Analysis tab.
      </p>
    </div>
    """, unsafe_allow_html=True)

    # ── Upload zones ──
    left, right = st.columns([3, 2], gap="large")

    with left:
        st.markdown('<p style="font-family:IBM Plex Sans;font-size:.62rem;font-weight:700;letter-spacing:.1em;text-transform:uppercase;color:#f59e0b;margin-bottom:8px">● Required — upload every week</p>', unsafe_allow_html=True)
        c1, c2, c3 = st.columns(3)
        with c1: ss["up_v1"] = st.file_uploader("View 1 — Accounts",   type=["xlsx","xls"], key="fu_v1",    help="facility · OB · utilization · AM")
        with c2: ss["up_v2"] = st.file_uploader("View 2 — Invoices",   type=["xlsx","xls"], key="fu_v2",    help="stages · DPD · origination · settlement")
        with c3: ss["up_mh"] = st.file_uploader("Master Handover",     type=["xlsx","xls"], key="fu_mh",    help="Buyer_ID · AM · Account_Status")

        st.markdown('<p style="font-family:IBM Plex Sans;font-size:.62rem;font-weight:700;letter-spacing:.1em;text-transform:uppercase;color:#8b949e;margin:16px 0 8px">○ Optional — enables OB Trend &amp; Peak Analysis</p>', unsafe_allow_html=True)
        c4, c5 = st.columns(2)
        with c4: ss["up_obhist"] = st.file_uploader("Historical OB (File 5)", type=["xlsx","xls"], key="fu_obhist", help="Jun 2020 – Apr 2026")
        with c5: ss["up_obcurr"] = st.file_uploader("Current OB File",        type=["xlsx","xls"], key="fu_obcurr", help="May 2026 onwards")

    with right:
        # Status panel
        st.markdown('<p style="font-family:IBM Plex Sans;font-size:.62rem;font-weight:700;letter-spacing:.1em;text-transform:uppercase;color:#8b949e;margin-bottom:8px">Upload Status</p>', unsafe_allow_html=True)
        checks = [
            ("View 1 — Accounts",     bool(ss.get("up_v1")),     True),
            ("View 2 — Invoices",     bool(ss.get("up_v2")),     True),
            ("Master Handover",       bool(ss.get("up_mh")),     True),
            ("Historical OB",         bool(ss.get("up_obhist")), False),
            ("Current OB",            bool(ss.get("up_obcurr")), False),
        ]
        st.markdown(_file_status_html(checks), unsafe_allow_html=True)

        loaded_count = sum(1 for _, ok, req in checks if ok and req)
        req_count    = sum(1 for _, _, req in checks if req)
        prog_pct     = int(loaded_count / req_count * 100)
        bar_color    = "#10b981" if loaded_count == req_count else "#f59e0b"
        st.markdown(f"""
        <div style="margin-top:10px">
          <div style="display:flex;justify-content:space-between;font-family:'IBM Plex Mono',monospace;font-size:.65rem;color:#484f58;margin-bottom:4px">
            <span>Required files</span><span style="color:{bar_color}">{loaded_count}/{req_count}</span>
          </div>
          <div style="background:#21262d;border-radius:3px;height:4px;overflow:hidden">
            <div style="background:{bar_color};width:{prog_pct}%;height:4px;border-radius:3px;transition:width .3s"></div>
          </div>
        </div>
        """, unsafe_allow_html=True)

        # Date + launch
        st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
        ss["today_in"] = st.date_input("Today's Date (D.today)", value=date.today())
        st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)
        ready = loaded_count == req_count
        if st.button("LAUNCH DASHBOARD →", disabled=not ready, type="primary", use_container_width=True):
            with st.spinner("Processing files — first load takes ~30 seconds…"):
                try:
                    v1p = load_v1(ss["up_v1"]); v2p_ = load_v2(ss["up_v2"]); mhp = load_mh(ss["up_mh"])
                    obh = load_ob(ss["up_obhist"], lambda d: d < OB_CUTOFF)  if ss.get("up_obhist") else None
                    obc = load_ob(ss["up_obcurr"], lambda d: d >= OB_CUTOFF) if ss.get("up_obcurr") else None
                    today_ts = pd.Timestamp(ss["today_in"])
                    pod, v2p, ob_pivot = process_data(v1p, mhp, v2p_, obh, obc, today_ts)
                    ss["pod"] = pod; ss["v2p"] = v2p; ss["ob_pivot"] = ob_pivot
                    ss["today_ts"] = today_ts; ss["loaded"] = True
                    st.rerun()
                except Exception as e:
                    st.error(f"Error loading files: {e}")
                    import traceback; st.code(traceback.format_exc())

if not ss.get("loaded"):
    show_upload()
    st.stop()

# ══════════════════════════════════════════════════════════════════════════════
# MAIN APP
# ══════════════════════════════════════════════════════════════════════════════
pod      = ss["pod"]; v2p_all = ss["v2p"]; ob_pivot = ss["ob_pivot"]; today_ts = ss["today_ts"]
sorted_ob_keys = sorted(ob_pivot.index) if not ob_pivot.empty else []

# ── App Header ────────────────────────────────────────────────
c_logo, c_am, c_actions = st.columns([3, 6, 2])
with c_logo:
    st.markdown(f"""<div style="display:flex;align-items:center;gap:10px;padding:4px 0">
      <div style="font-family:'IBM Plex Sans',sans-serif;font-size:1rem;font-weight:700;letter-spacing:.04em;color:#e6edf3">CP POD <span style="color:#f59e0b">·</span> SCF</div>
      <div style="background:rgba(245,158,11,.12);border:1px solid rgba(245,158,11,.3);color:#f59e0b;font-family:'IBM Plex Mono',monospace;font-size:.65rem;padding:2px 9px;border-radius:12px">{today_ts.strftime('%d %b %Y')}</div>
    </div>""", unsafe_allow_html=True)
with c_am:
    am_opts = ["All"] + POD_AMS; am_lbls = ["All","NS","DH","DD","AN","AA"]
    gam_i = st.radio("Filter by AM", range(len(am_opts)), format_func=lambda i: am_lbls[i],
                     horizontal=True, label_visibility="collapsed", key="gam")
    global_am = am_opts[gam_i]
with c_actions:
    if st.button("↑ Re-upload", use_container_width=True):
        ss["loaded"] = False; st.rerun()

st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)

fa  = pod    if global_am == "All" else pod[pod["am"] == global_am]
v2f = v2p_all if global_am == "All" else v2p_all[v2p_all["am"] == global_am]

# ── Tab navigation ────────────────────────────────────────────
tabs = st.tabs([
    "📊 Snapshot", "📁 Portfolio", "👥 Team", "🏥 Health",
    "⚡ Actions", "🔍 Account Pulse", "📋 Tracker", "📈 Peak", "🏦 CP Health"
])

# ══════════════════════════════════════════════════════════════
# F · EXECUTIVE SNAPSHOT
# ══════════════════════════════════════════════════════════════
with tabs[0]:
    tgt = fa[fa["level2"].isin(["Active Workable","Suspended Workable"])]
    aw  = fa[fa["level2"]=="Active Workable"]; sw = fa[fa["level2"]=="Suspended Workable"]
    tot_ob = tgt["ob"].sum(); tot_fac = tgt["total_fac"].sum()
    open_inv = v2f[v2f["Stage"].isin(OPEN_ST)]
    ov_inv   = open_inv[(open_inv["dpd"]>7)&(open_inv["dpd"]<=90)]
    npa_inv  = open_inv[open_inv["dpd"]>90]
    ov_ob    = ov_inv["Outstanding"].sum(); npa_ob = npa_inv["Outstanding"].sum()
    clean_ob = max(0, tot_ob - ov_ob - npa_ob)
    util_pct = tot_ob / tot_fac if tot_fac else 0

    st.markdown(section_header("Portfolio Scale"), unsafe_allow_html=True)
    c1,c2,c3,c4 = st.columns(4)
    c1.markdown(kpi_card("Total OB", fmt_ccy(tot_ob), f"{len(tgt)} in-target WA accounts", "amber"), unsafe_allow_html=True)
    c2.markdown(kpi_card("Total Facility", fmt_ccy(tot_fac), "Facility + Overdraft", "muted"), unsafe_allow_html=True)
    c3.markdown(kpi_card("Portfolio Utilization", fmt_pct(util_pct), "OB / Total Facility",
        "green" if util_pct > 0.6 else "orange"), unsafe_allow_html=True)
    c4.markdown(kpi_card("Total Accounts", str(len(fa)),
        f"{len(fa[fa['broad']=='Workable'])} Workable · {len(fa[fa['level2']=='NWA'])} NWA", "muted"), unsafe_allow_html=True)

    st.markdown(section_header("Account Health Breakdown"), unsafe_allow_html=True)
    cats = [
        ("Active Workable",   "Active Workable",  "green",  "IN TARGET"),
        ("Suspended Workable","Suspended Workable","orange", "IN TARGET"),
        ("Workable_Over365",  "WA >365 Days",     "muted",  "EXCLUDED"),
        ("NWA",               "Non-Workable",      "muted",  "NWA"),
    ]
    cols = st.columns(4)
    for (key, label, color, tag), col in zip(cats, cols):
        sub = fa[fa["level2"]==key]
        col.markdown(kpi_card(label, str(len(sub)),
            f"{fmt_ccy(sub['ob'].sum())} OB · {badge(tag, 'target' if tag=='IN TARGET' else 'nwa')}", color),
            unsafe_allow_html=True)

    st.markdown(section_header("Yield — Weighted IRR"), unsafe_allow_html=True)
    c1,c2,c3 = st.columns(3)
    c1.markdown(kpi_card("Portfolio WIRR",    fmt_irr(wirr(tgt)), "All WA accounts",       "amber"), unsafe_allow_html=True)
    c2.markdown(kpi_card("Active WA WIRR",    fmt_irr(wirr(aw)),  "In-target, active",     "green"), unsafe_allow_html=True)
    c3.markdown(kpi_card("Suspended WA WIRR", fmt_irr(wirr(sw)),  "In-target, suspended",  "orange"), unsafe_allow_html=True)

    st.markdown(section_header("Risk"), unsafe_allow_html=True)
    c1,c2,c3 = st.columns(3)
    c1.markdown(kpi_card("Overdue (DPD 8–90)", fmt_ccy(ov_ob),   f"{len(ov_inv)} invoices outstanding",  "red"),    unsafe_allow_html=True)
    c2.markdown(kpi_card("NPA (DPD > 90)",     fmt_ccy(npa_ob),  f"{len(npa_inv)} invoices outstanding", "red"),    unsafe_allow_html=True)
    c3.markdown(kpi_card("Clean OB",           fmt_ccy(clean_ob), fmt_pct(clean_ob/tot_ob if tot_ob else 0)+" of portfolio", "green"), unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════
# A · PORTFOLIO
# ══════════════════════════════════════════════════════════════
with tabs[1]:
    tgt  = fa[fa["level2"].isin(["Active Workable","Suspended Workable"])]
    aw   = fa[fa["level2"]=="Active Workable"];  sw   = fa[fa["level2"]=="Suspended Workable"]
    nwa  = fa[fa["level2"]=="NWA"];              o365 = fa[fa["level2"]=="Workable_Over365"]
    open_inv = v2f[v2f["Stage"].isin(OPEN_ST)]
    ov_ob  = open_inv[(open_inv["dpd"]>7)&(open_inv["dpd"]<=90)]["Outstanding"].sum()
    npa_ob = open_inv[open_inv["dpd"]>90]["Outstanding"].sum()
    tot_ob = tgt["ob"].sum(); clean_ob = max(0, tot_ob - ov_ob - npa_ob)
    ov_cos  = set(open_inv[(open_inv["dpd"]>7)&(open_inv["dpd"]<=90)]["buyer_lower"])
    npa_cos = set(open_inv[open_inv["dpd"]>90]["buyer_lower"])

    # Portfolio Quality
    st.markdown(section_header("Portfolio Quality"), unsafe_allow_html=True)
    c1,c2,c3 = st.columns(3)
    c1.markdown(kpi_card("Clean OB",              fmt_ccy(clean_ob), fmt_pct(clean_ob/tot_ob if tot_ob else 0)+" of portfolio", "green"), unsafe_allow_html=True)
    c2.markdown(kpi_card("Overdue OB (DPD 8–90)", fmt_ccy(ov_ob),   f"{len(open_inv[(open_inv['dpd']>7)&(open_inv['dpd']<=90)])} invoices", "orange"), unsafe_allow_html=True)
    c3.markdown(kpi_card("NPA OB (DPD > 90)",     fmt_ccy(npa_ob),  f"{len(open_inv[open_inv['dpd']>90])} invoices", "red"), unsafe_allow_html=True)

    cl, cr = st.columns([1, 2])
    with cl:
        fig = go.Figure(go.Pie(labels=["Clean","Overdue","NPA"],
            values=[clean_ob/1e6, ov_ob/1e6, npa_ob/1e6], hole=0.65,
            marker_colors=["#10b981","#f97316","#ef4444"],
            textinfo="none",
            hovertemplate="<b>%{label}</b><br>$%{value:.2f}M<extra></extra>"))
        fig.add_annotation(text=fmt_pct(clean_ob/tot_ob if tot_ob else 0),
            x=0.5, y=0.55, font=dict(family="IBM Plex Mono", size=20, color="#10b981"), showarrow=False)
        fig.add_annotation(text="CLEAN", x=0.5, y=0.4,
            font=dict(family="IBM Plex Sans", size=9, color="#484f58"), showarrow=False)
        fig.update_layout(**plotly_layout(height=240, showlegend=True,
            legend=dict(orientation="h", y=-0.15, x=0.5, xanchor="center")))
        st.plotly_chart(fig, use_container_width=True)

    with cr:
        pq_filter = st.selectbox("Filter accounts", ["All","Clean","Overdue","NPA"], key="pq_f", label_visibility="collapsed")
        pq = tgt.copy()
        pq["Status"] = pq["company"].str.lower().apply(lambda c: "NPA" if c in npa_cos else ("Overdue" if c in ov_cos else "Clean"))
        if pq_filter != "All": pq = pq[pq["Status"]==pq_filter]
        pq = pq.sort_values("ob", ascending=False)
        pq["Util %"] = pq.apply(lambda r: min(r["ob"]/r["total_fac"],1) if r["total_fac"]>0 else 0, axis=1)
        d = pq[["company","am","Status","total_fac","ob","Util %"]].copy()
        d.columns = ["Company","AM","Status","Facility ($)","OB ($)","Util"]
        d["Facility ($)"] = d["Facility ($)"].apply(fmt_ccy); d["OB ($)"] = d["OB ($)"].apply(fmt_ccy)
        d["Util"] = d["Util"].apply(fmt_pct)
        st.dataframe(d.reset_index(drop=True), use_container_width=True, height=240,
            column_config={"Status": st.column_config.TextColumn("Status", width="small")})

    # Weighted IRR
    st.markdown(section_header("Weighted IRR"), unsafe_allow_html=True)
    thresh = st.number_input("OB Threshold ≥ $", value=0, min_value=0, step=1000, key="a_thresh",
                             help="Exclude accounts below this OB from IRR calculation")
    c1,c2,c3 = st.columns(3)
    c1.markdown(kpi_card("Portfolio WIRR",    fmt_irr(wirr(tgt,"ob","irr",thresh)), "All WA in-target", "amber"), unsafe_allow_html=True)
    c2.markdown(kpi_card("Active WA WIRR",    fmt_irr(wirr(aw,"ob","irr",thresh)),  "Active workable",  "green"), unsafe_allow_html=True)
    c3.markdown(kpi_card("Suspended WA WIRR", fmt_irr(wirr(sw,"ob","irr",thresh)),  "Suspended workable","orange"), unsafe_allow_html=True)

    # Targetable portfolio
    st.markdown(section_header("Targetable Portfolio"), unsafe_allow_html=True)
    panels = [("🟢 Active WA",aw,"IN TARGET","green"),("🟠 Suspended WA",sw,"IN TARGET","orange"),
              ("⏸ WA >365d",o365,"EXCLUDED","muted"),("⛔ Non-Workable",nwa,"NWA","muted")]
    for (lbl, arr, tag, color), col in zip(panels, st.columns(4)):
        ob = arr["ob"].sum(); fac = arr["total_fac"].sum()
        col.markdown(kpi_card(lbl, str(len(arr)),
            f"{fmt_ccy(ob)} OB · {fmt_pct(ob/fac if fac else 0)} util · {badge(tag,'target' if 'TARGET' in tag else 'nwa')}", color),
            unsafe_allow_html=True)

    # Origination vs Repayment
    st.markdown(section_header("Origination vs Repayment"), unsafe_allow_html=True)
    ovr_win = st.radio("", ["MTD","QTD"], horizontal=True, key="ovr_win", label_visibility="collapsed")
    s_ovr, e_ovr = get_window("mtd" if ovr_win=="MTD" else "qtd", today_ts)
    ao = {a:0 for a in POD_AMS+["Team"]}; ar = {a:0 for a in POD_AMS+["Team"]}
    for _, inv in v2f.iterrows():
        if inv["Stage"] in EXCL_ST or inv["am"] not in POD_AMS: continue
        if pd.notna(inv["disbursed_date"]) and in_win(inv["disbursed_date"],s_ovr,e_ovr):
            ao[inv["am"]] += inv["Origination"]; ao["Team"] += inv["Origination"]
        if inv["Stage"] in SETTLED|{"partial"} and pd.notna(inv["settlement_date"]) and in_win(inv["settlement_date"],s_ovr,e_ovr):
            r = max(0,inv["Origination"]-inv["Outstanding"]); ar[inv["am"]] += r; ar["Team"] += r
    short = [a.split()[0] for a in POD_AMS]; keys = [*POD_AMS,"Team"]; lbls = [*short,"Team"]
    nets  = [(ao[k]-ar[k])/1e6 for k in keys]
    fig = go.Figure()
    fig.add_trace(go.Bar(x=lbls, y=[ao[k]/1e6 for k in keys], name="Originated", marker_color="#6366f1", marker_opacity=0.85))
    fig.add_trace(go.Bar(x=lbls, y=[ar[k]/1e6 for k in keys], name="Repaid",     marker_color="#10b981", marker_opacity=0.75))
    fig.add_trace(go.Bar(x=lbls, y=nets, name="Net",
        marker_color=["#f59e0b" if v>=0 else "#ef4444" for v in nets], marker_opacity=0.9))
    fig.update_layout(**plotly_layout(height=260, barmode="group", yaxis_tickprefix="$", yaxis_ticksuffix="M"))
    st.plotly_chart(fig, use_container_width=True)

    # Collections
    st.markdown(section_header("Collections Tracker"), unsafe_allow_html=True)
    col_d, col_w = st.columns([2,4])
    with col_d:
        c_am = st.selectbox("AM", ["All"]+POD_AMS, key="c_am",
                            format_func=lambda x: "All AMs" if x=="All" else x)
    with col_w:
        c_win = st.radio("", ["Curr Wk","Next Wk","Curr Mo","Next Mo"], horizontal=True, key="c_win", label_visibility="collapsed")
    cw_map = {"Curr Wk":"cw","Next Wk":"nw","Curr Mo":"cm","Next Mo":"nm"}
    ci = v2f if c_am=="All" else v2f[v2f["am"]==c_am]
    ms = pd.Timestamp(today_ts.year, today_ts.month, 1)
    recv  = ci[ci["Stage"].isin(SETTLED)&ci["settlement_date"].notna()&
               ci["settlement_date"].apply(lambda d: in_win(d,ms,today_ts))
               ].apply(lambda r: max(0,r["Origination"]-r["Outstanding"]),axis=1).sum()
    ws, we = get_window(cw_map[c_win], today_ts)
    tr_inv = ci[ci["Stage"].isin({"advanced","partial"})&ci["due_date_of_invoice"].notna()&
                ci["due_date_of_invoice"].apply(lambda d: in_win(d,ws,we))]
    rec = ci[ci["Stage"].isin({"overdue","npa"})].apply(lambda r: max(0,r["Origination"]-r["Outstanding"]),axis=1).sum()
    c1,c2,c3 = st.columns(3)
    c1.markdown(kpi_card("✅ Received MTD",  fmt_ccy(recv), "Principal repaid this month", "green"),  unsafe_allow_html=True)
    c2.markdown(kpi_card("⏳ To Receive",    fmt_ccy(tr_inv["Outstanding"].sum()), f"{len(tr_inv)} invoices due · {c_win.lower()}", "amber"), unsafe_allow_html=True)
    c3.markdown(kpi_card("⚠ Recovery",       fmt_ccy(rec),  "Overdue + NPA — tracked separately", "orange"), unsafe_allow_html=True)
    by_co = tr_inv.groupby("Buyer").agg(AM=("am","first"),Invoices=("Invoice ID","count"),
        Total=("Outstanding","sum"),MinDue=("due_date_of_invoice","min"),MaxDue=("due_date_of_invoice","max")).sort_values("Total",ascending=False)
    by_co["Total"]=by_co["Total"].apply(fmt_ccy)
    by_co["Due Range"]=by_co.apply(lambda r: fmt_date(r["MinDue"])+("" if r["MinDue"]==r["MaxDue"] else " → "+fmt_date(r["MaxDue"])),axis=1)
    with st.expander(f"To Receive — Account Detail  ({len(by_co)} companies)"):
        st.dataframe(by_co[["AM","Invoices","Total","Due Range"]].reset_index(), use_container_width=True)

# ══════════════════════════════════════════════════════════════
# B · TEAM PERFORMANCE
# ══════════════════════════════════════════════════════════════
with tabs[2]:
    st.markdown(section_header("AM Scorecards"), unsafe_allow_html=True)
    ms = pd.Timestamp(today_ts.year, today_ts.month, 1)
    ams_show = [global_am] if global_am != "All" else POD_AMS
    cols = st.columns(len(ams_show))
    for am, col, color in zip(ams_show, cols, AM_COLORS):
        accts = fa[fa["am"]==am]
        aw_ = accts[accts["level2"]=="Active Workable"]; sw_ = accts[accts["level2"]=="Suspended Workable"]
        ai  = v2f[v2f["am"]==am]
        orig_mtd = ai[ai["disbursed_date"].notna()&ai["disbursed_date"].apply(lambda d: in_win(d,ms,today_ts))]["Origination"].sum()
        rep_mtd  = ai[ai["Stage"].isin(SETTLED|{"partial"})&ai["settlement_date"].notna()&
                      ai["settlement_date"].apply(lambda d: in_win(d,ms,today_ts))
                      ].apply(lambda r: max(0,r["Origination"]-r["Outstanding"]),axis=1).sum()
        early_mtd = ai[ai["Stage"].isin(SETTLED)&ai["settlement_date"].notna()&
                       ai["due_date_of_invoice"].notna()&(ai["settlement_date"]<ai["due_date_of_invoice"])&
                       ai["settlement_date"].apply(lambda d: in_win(d,ms,today_ts))]["Origination"].sum()
        irr_val = wirr(accts[accts["level2"].isin(["Active Workable","Suspended Workable"])])
        col.markdown(am_scorecard(am, AM_INIT.get(am,"??"), color, [
            ("Active WA OB",   fmt_ccy(aw_["ob"].sum()),   "#f59e0b"),
            ("Active WA Fac",  fmt_ccy(aw_["total_fac"].sum()), "#8b949e"),
            ("Active WA Util", fmt_pct(aw_["ob"].sum()/aw_["total_fac"].sum() if aw_["total_fac"].sum()>0 else 0), "#8b949e"),
            ("Suspended WA OB",fmt_ccy(sw_["ob"].sum()),   "#f97316"),
            ("MTD Originated", fmt_ccy(orig_mtd),          "#6366f1"),
            ("MTD Repaid",     fmt_ccy(rep_mtd),           "#10b981"),
            ("MTD Early Repay",fmt_ccy(early_mtd),         "#10b981"),
            ("WIRR",           fmt_irr(irr_val),           "#f59e0b"),
        ]), unsafe_allow_html=True)

    st.markdown(section_header("Status Distribution"), unsafe_allow_html=True)
    aw_c,sw_c,o_c,n_c = [],[],[],[]
    for am in POD_AMS:
        a=fa[fa["am"]==am]
        aw_c.append(len(a[a["level2"]=="Active Workable"])); sw_c.append(len(a[a["level2"]=="Suspended Workable"]))
        o_c.append(len(a[a["level2"]=="Workable_Over365"]));  n_c.append(len(a[a["level2"]=="NWA"]))
    fig = go.Figure()
    for data,name,color in [(aw_c,"Active Workable","#10b981"),(sw_c,"Suspended WA","#f97316"),
                             (o_c,">365d","#484f58"),(n_c,"NWA","#30363d")]:
        fig.add_trace(go.Bar(x=[a.split()[0] for a in POD_AMS],y=data,name=name,marker_color=color))
    fig.update_layout(**plotly_layout(height=260, barmode="stack"))
    st.plotly_chart(fig, use_container_width=True)

# ══════════════════════════════════════════════════════════════
# C · BOOK HEALTH
# ══════════════════════════════════════════════════════════════
with tabs[3]:
    wa = fa[fa["level2"].isin(["Active Workable","Suspended Workable"])].copy()
    wa["util"]   = wa.apply(lambda r: min(r["ob"]/r["total_fac"],1) if r["total_fac"]>0 else 0, axis=1)
    wa["bucket"] = wa["util"].apply(lambda u: "Zero" if u<=0 else ("Low" if u<=0.4 else ("Medium" if u<=0.74 else "High")))
    br = {"Zero":"0%","Low":"1–40%","Medium":"41–74%","High":"75–100%"}
    bc = {"Zero":"#484f58","Low":"#f59e0b","Medium":"#6366f1","High":"#10b981"}

    st.markdown(section_header("Utilization Buckets"), unsafe_allow_html=True)
    for bk, col in zip(["Zero","Low","Medium","High"], st.columns(4)):
        sub = wa[wa["bucket"]==bk]
        col.markdown(kpi_card(f"{bk}  ({br[bk]})", str(len(sub)),
            f"{fmt_ccy(sub['ob'].sum())} OB",
            {k: v for k,v in [("Zero","muted"),("Low","amber"),("Medium","muted"),("High","green")]}[bk]),
            unsafe_allow_html=True)

    cl, cr = st.columns([1,2])
    with cl:
        fig = go.Figure(go.Pie(labels=[f"{k} ({br[k]})" for k in ["Zero","Low","Medium","High"]],
            values=[wa[wa["bucket"]==k]["ob"].sum()/1e6 for k in ["Zero","Low","Medium","High"]],
            hole=0.6, marker_colors=[bc[k] for k in ["Zero","Low","Medium","High"]],
            textinfo="none", hovertemplate="<b>%{label}</b><br>$%{value:.2f}M<extra></extra>"))
        fig.update_layout(**plotly_layout(height=240, showlegend=True,
            legend=dict(orientation="h", y=-0.2, x=0.5, xanchor="center")))
        st.plotly_chart(fig, use_container_width=True)
    with cr:
        bsel = st.selectbox("View bucket", ["All","Zero","Low","Medium","High"], key="bsel", label_visibility="collapsed")
        bd = (wa if bsel=="All" else wa[wa["bucket"]==bsel]).sort_values("ob",ascending=False).copy()
        bd["Facility"]=bd["total_fac"].apply(fmt_ccy); bd["OB"]=bd["ob"].apply(fmt_ccy); bd["Util %"]=bd["util"].apply(fmt_pct)
        st.dataframe(bd[["company","am","level2","Facility","OB","Util %"]].rename(
            columns={"company":"Company","am":"AM","level2":"Status"}).reset_index(drop=True),
            use_container_width=True, height=240)

    st.markdown(section_header("Overdue Invoices", "DPD 8–90"), unsafe_allow_html=True)
    open_inv = v2f[v2f["Stage"].isin(OPEN_ST)]
    ov = open_inv[(open_inv["dpd"]>7)&(open_inv["dpd"]<=90)].copy()
    npa = open_inv[open_inv["dpd"]>90].copy()
    for lbl, inv_df, color in [("Overdue (DPD 8–90)",ov,"orange"),("NPA — Non-Performing (DPD > 90)",npa,"red")]:
        tot = inv_df["Outstanding"].sum(); par = inv_df[(inv_df["Origination"]-inv_df["Outstanding"])>0]
        c1,c2,c3 = st.columns(3)
        c1.markdown(kpi_card(f"{lbl}", fmt_ccy(tot), f"{len(inv_df)} invoices", color), unsafe_allow_html=True)
        c2.markdown(kpi_card("No Payment Received", fmt_ccy(inv_df[~inv_df.index.isin(par.index)]["Outstanding"].sum()),
            f"{len(inv_df)-len(par)} invoices","muted"), unsafe_allow_html=True)
        c3.markdown(kpi_card("Partially Recovered", fmt_ccy(par["Outstanding"].sum()),
            f"{len(par)} invoices · {fmt_ccy((par['Origination']-par['Outstanding']).sum())} recovered","green"), unsafe_allow_html=True)
        d = inv_df.copy(); d["Recovered"]=(d["Origination"]-d["Outstanding"]).clip(lower=0).apply(fmt_ccy)
        d["Origination"]=d["Origination"].apply(fmt_ccy); d["Outstanding"]=d["Outstanding"].apply(fmt_ccy)
        with st.expander(f"{lbl} — Full Detail  ({len(inv_df)} invoices)"):
            st.dataframe(d[["Buyer","am","Invoice ID","Stage","Origination","Outstanding","dpd","Recovered"]].reset_index(drop=True), use_container_width=True)

    st.markdown(section_header("Days Since Last Disbursement"), unsafe_allow_html=True)
    db  = st.selectbox("Filter by bucket", ["All","0-30","31-60","61-90","91-120","121-150","151-180","180+"], key="dsld")
    wda = fa[fa["level2"].isin(["Active Workable","Suspended Workable","Workable_Over365"])].copy()
    if db != "All":
        if db=="180+": wda=wda[wda["days_since"].notna()&(wda["days_since"]>=180)]
        else:
            lo,hi=map(int,db.split("-")); wda=wda[wda["days_since"].notna()&(wda["days_since"]>=lo)&(wda["days_since"]<=hi)]
    wda=wda.sort_values("days_since",ascending=False)
    d=wda[["company","am","level2","last_disb","days_since"]].copy()
    d["last_disb"]=d["last_disb"].apply(fmt_date); d.columns=["Company","AM","Status","Last Disbursed","Days Since"]
    st.dataframe(d.reset_index(drop=True), use_container_width=True, height=350)

# ══════════════════════════════════════════════════════════════
# D · ACTION BOARD
# ══════════════════════════════════════════════════════════════
with tabs[4]:
    st.markdown(section_header("Declining Accounts", "Repayments exceeded originations in window"), unsafe_allow_html=True)
    dw = st.radio("Window", ["MTD","QTD"], horizontal=True, key="dw", label_visibility="collapsed")
    sd, ed = get_window("mtd" if dw=="MTD" else "qtd", today_ts)
    amap={}
    for _,inv in v2f.iterrows():
        if inv["level2"] in ["NWA","Workable_Over365"]: continue
        co=inv["Buyer"]
        if co not in amap: amap[co]={"am":inv["am"],"level2":inv["level2"],"orig":0,"rep":0}
        if pd.notna(inv["disbursed_date"]) and in_win(inv["disbursed_date"],sd,ed): amap[co]["orig"]+=inv["Origination"]
        if inv["Stage"] in SETTLED|{"partial"} and pd.notna(inv["settlement_date"]) and in_win(inv["settlement_date"],sd,ed):
            amap[co]["rep"]+=max(0,inv["Origination"]-inv["Outstanding"])
    decl=[(co,v) for co,v in amap.items() if v["rep"]>v["orig"]]; decl.sort(key=lambda x:x[1]["orig"]-x[1]["rep"])
    if decl:
        t15=decl[:15]
        fig=go.Figure(go.Bar(x=[v["orig"]-v["rep"] for _,v in t15],y=[co[:24] for co,_ in t15],
            orientation="h",marker_color=["#ef4444" if v["orig"]-v["rep"]<0 else "#10b981" for _,v in t15],
            marker_opacity=0.85, hovertemplate="<b>%{y}</b><br>Net: $%{x:,.0f}<extra></extra>"))
        fig.update_layout(**plotly_layout(height=max(280,len(t15)*28), xaxis_tickprefix="$"))
        st.plotly_chart(fig, use_container_width=True)
    dd=pd.DataFrame([{"Company":co,"AM":v["am"],"Originated":fmt_ccy(v["orig"]),"Repaid":fmt_ccy(v["rep"]),"Net":fmt_ccy(v["orig"]-v["rep"]),"Status":v["level2"]} for co,v in decl])
    with st.expander(f"Full Declining List  ({len(decl)} accounts)"):
        st.dataframe(dd.reset_index(drop=True) if not dd.empty else pd.DataFrame(), use_container_width=True)

    st.markdown(section_header("High Opportunity", "Headroom + upcoming repayments"), unsafe_allow_html=True)
    ow=st.radio("Due in",["Curr Wk","Next Wk","Curr Mo","Next Mo"],horizontal=True,key="ow",label_visibility="collapsed")
    ow_map={"Curr Wk":"cw","Next Wk":"nw","Curr Mo":"cm","Next Mo":"nm"}
    ws,we=get_window(ow_map[ow],today_ts); dbc={}
    for _,inv in v2f.iterrows():
        if inv["Stage"] not in {"advanced","partial"}: continue
        if pd.notna(inv["due_date_of_invoice"]) and in_win(inv["due_date_of_invoice"],ws,we):
            dbc[inv["buyer_lower"]]=dbc.get(inv["buyer_lower"],0)+inv["Outstanding"]
    wo=fa[fa["level2"].isin(["Active Workable","Suspended Workable"])].copy()
    wo["headroom"]=(wo["total_fac"]-wo["ob"]).clip(lower=0); wo["due"]=wo["company"].str.lower().map(dbc).fillna(0)
    wo["opp"]=wo["headroom"]+wo["due"]; wo=wo[wo["opp"]>0].sort_values("opp",ascending=False)
    od=wo[["company","am","headroom","due","opp","level2"]].copy()
    od["headroom"]=od["headroom"].apply(fmt_ccy); od["due"]=od["due"].apply(fmt_ccy); od["opp"]=od["opp"].apply(fmt_ccy)
    od.columns=["Company","AM","Headroom","Due Repayments","Total Opportunity","Status"]
    with st.expander(f"High Opportunity  ({len(wo)} accounts)"):
        st.dataframe(od.reset_index(drop=True), use_container_width=True)

    st.markdown(section_header("Early Repayment Tracking"), unsafe_allow_html=True)
    early=v2f[v2f["Stage"].isin(SETTLED)&v2f["settlement_date"].notna()&
              v2f["due_date_of_invoice"].notna()&(v2f["settlement_date"]<v2f["due_date_of_invoice"])].copy()
    early["days_early"]=(early["due_date_of_invoice"]-early["settlement_date"]).dt.days
    early=early.sort_values("days_early",ascending=False)
    st.markdown(stat_row([
        ("Early Repayments", str(len(early)), "#f59e0b"),
        ("Total Value", fmt_ccy(early["Origination"].sum()), "#10b981"),
        ("Avg Days Early", str(int(early["days_early"].mean())) if len(early) else "—", "#8b949e"),
    ]), unsafe_allow_html=True)
    ed2=early[["Buyer","am","Invoice ID","Origination","settlement_date","due_date_of_invoice","days_early"]].copy()
    ed2["Origination"]=ed2["Origination"].apply(fmt_ccy); ed2["settlement_date"]=ed2["settlement_date"].apply(fmt_date); ed2["due_date_of_invoice"]=ed2["due_date_of_invoice"].apply(fmt_date)
    ed2.columns=["Company","AM","Invoice ID","Origination","Settlement","Due Date","Days Early"]
    with st.expander(f"Early Repayments  ({len(early)} invoices)"):
        st.dataframe(ed2.reset_index(drop=True), use_container_width=True)

    st.markdown(section_header("Reactivation Focus", "Suspended · ≥180 days dormant · sorted by Peak OB"), unsafe_allow_html=True)
    react=fa[(fa["broad"]=="Workable")&(fa["v1_util"]=="suspended")&fa["days_since"].notna()&(fa["days_since"]>=180)].sort_values("peak_ob",ascending=False).copy()
    if len(react)==0: st.markdown(info_banner("No suspended accounts dormant for ≥180 days.","tip"), unsafe_allow_html=True)
    else:
        rd=react[["company","am","total_fac","ob","peak_ob","avg_ob","days_since"]].copy()
        for c in ["total_fac","ob","peak_ob","avg_ob"]: rd[c]=rd[c].apply(fmt_ccy)
        rd.columns=["Company","AM","Total Facility","Current OB","Peak OB","Avg OB","Days Dormant"]
        with st.expander(f"Reactivation List  ({len(react)} accounts)"):
            st.dataframe(rd.reset_index(drop=True), use_container_width=True)

# ══════════════════════════════════════════════════════════════
# H · ACCOUNT PULSE
# ══════════════════════════════════════════════════════════════
with tabs[5]:
    wa=fa[fa["level2"].isin(["Active Workable","Suspended Workable"])].copy()
    wa["util"]=wa.apply(lambda r: min(r["ob"]/r["total_fac"],1) if r["total_fac"]>0 else 0, axis=1)
    ob30_map, ob90_map = {}, {}
    if not ob_pivot.empty:
        k30=closest_before((today_ts-timedelta(days=30)).date(),sorted_ob_keys)
        k90=closest_before((today_ts-timedelta(days=90)).date(),sorted_ob_keys)
        if k30 and k30 in ob_pivot.index: ob30_map=ob_pivot.loc[k30].to_dict()
        if k90 and k90 in ob_pivot.index: ob90_map=ob_pivot.loc[k90].to_dict()
    wa["ob30"]=wa["id"].map(ob30_map).fillna(0); wa["ob90"]=wa["id"].map(ob90_map).fillna(0)
    wa["chg30"]=wa["ob"]-wa["ob30"]

    st.markdown(section_header("Workable Accounts"), unsafe_allow_html=True)
    r1c1, r1c2, r1c3 = st.columns([2,3,3])
    with r1c1: h_sort=st.radio("Sort",["Facility","OB","Util %"],horizontal=True,key="hs",label_visibility="collapsed")
    with r1c2: h_n=st.radio("Show",["Top 10","Top 25","Top 50","All","Bot 50"],horizontal=True,key="hn",label_visibility="collapsed")
    with r1c3: h_rw=st.radio("Highlight Due",["None","This Week","This Month","Next Month"],horizontal=True,key="hrw",label_visibility="collapsed")
    sort_c={"Facility":"total_fac","OB":"ob","Util %":"util"}[h_sort]
    ws_=wa.sort_values(sort_c,ascending=False)
    w_disp=ws_ if h_n=="All" else (ws_.tail(50) if h_n.startswith("Bot") else ws_.head(int(h_n.split()[-1])))
    rw_map={"None":None,"This Week":"cw","This Month":"cm","Next Month":"nm"}
    due_hl={}
    if rw_map[h_rw]:
        ws2,we2=get_window(rw_map[h_rw],today_ts)
        for _,inv in v2f.iterrows():
            if inv["Stage"] not in {"advanced","partial"}: continue
            if pd.notna(inv["due_date_of_invoice"]) and in_win(inv["due_date_of_invoice"],ws2,we2):
                due_hl[inv["buyer_lower"]]=due_hl.get(inv["buyer_lower"],0)+inv["Outstanding"]
    w_disp=w_disp.copy(); w_disp["due"]=w_disp["company"].str.lower().map(due_hl).fillna(0)
    wd=w_disp[["company","am","level2","total_fac","ob","util","chg30","due","last_disb","peak_ob","avg_ob"]].copy()
    for c in ["total_fac","ob","peak_ob","avg_ob"]: wd[c]=wd[c].apply(fmt_ccy)
    wd["util"]=wd["util"].apply(fmt_pct); wd["chg30"]=wd["chg30"].apply(lambda v:("+" if v>=0 else "")+fmt_ccy(v))
    wd["due"]=wd["due"].apply(lambda v:fmt_ccy(v) if v>0 else "—"); wd["last_disb"]=wd["last_disb"].apply(fmt_date)
    wd.columns=["Company","AM","Status","Total Facility","OB","Util %","OB Δ30d","Due (Sel)","Last Disb","Peak OB","Avg OB"]
    st.dataframe(wd.reset_index(drop=True), use_container_width=True, height=400)

    col_l, col_r = st.columns(2)
    with col_l:
        st.markdown(section_header("About to Go Inactive", "Active WA · ≥120 days since last disbursement"), unsafe_allow_html=True)
        inact=wa[(wa["level2"]=="Active Workable")&wa["days_since"].notna()&(wa["days_since"]>=120)].sort_values("days_since",ascending=False)
        st.markdown(stat_row([
            ("At Risk", str(len(inact)), "#f97316"),
            ("OB at Risk", fmt_ccy(inact["ob"].sum()), "#f59e0b"),
            ("Facility at Risk", fmt_ccy(inact["total_fac"].sum()), "#8b949e"),
        ]), unsafe_allow_html=True)
        ind=inact[["company","am","total_fac","ob","util","last_disb","days_since","peak_ob"]].copy()
        for c in ["total_fac","ob","peak_ob"]: ind[c]=ind[c].apply(fmt_ccy)
        ind["util"]=ind["util"].apply(fmt_pct); ind["last_disb"]=ind["last_disb"].apply(fmt_date)
        ind.columns=["Company","AM","Facility","OB","Util %","Last Disb","Days","Peak OB"]
        with st.expander(f"Inactive Risk  ({len(inact)})"):
            st.dataframe(ind.reset_index(drop=True), use_container_width=True)

    with col_r:
        st.markdown(section_header("Headroom Opportunity", "Excludes dormant ≥120 days"), unsafe_allow_html=True)
        hr=wa[wa["days_since"].fillna(0)<120].copy()
        hr["headroom"]=(hr["total_fac"]-hr["ob"]).clip(lower=0); hr["peak_gap"]=(hr["peak_ob"]-hr["ob"]).clip(lower=0)
        hr=hr[hr["headroom"]>0].sort_values("headroom",ascending=False)
        st.markdown(stat_row([
            ("Accounts", str(len(hr)), "#f59e0b"),
            ("Total Headroom", fmt_ccy(hr["headroom"].sum()), "#10b981"),
            ("Avg Headroom", fmt_ccy(hr["headroom"].mean()) if len(hr) else "—", "#8b949e"),
        ]), unsafe_allow_html=True)
        hrd=hr[["company","am","total_fac","ob","util","headroom","peak_ob","peak_gap"]].copy()
        for c in ["total_fac","ob","peak_ob"]: hrd[c]=hrd[c].apply(fmt_ccy)
        hrd["util"]=hrd["util"].apply(fmt_pct); hrd["headroom"]=hrd["headroom"].apply(fmt_ccy)
        hrd["peak_gap"]=hrd["peak_gap"].apply(lambda v:fmt_ccy(v) if v>0 else "—")
        hrd.columns=["Company","AM","Facility","OB","Util %","Headroom","Peak OB","Peak Gap"]
        with st.expander(f"Headroom Detail  ({len(hr)})"):
            st.dataframe(hrd.reset_index(drop=True), use_container_width=True)

    st.markdown(section_header("OB Drop", "Accounts where OB has declined"), unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    for col, ob_col, lbl in [(c1,"ob30","vs 30 Days Ago"),(c2,"ob90","vs 90 Days Ago")]:
        with col:
            st.markdown(f'<div style="font-family:IBM Plex Sans;font-size:.68rem;font-weight:600;color:#8b949e;margin-bottom:6px">{lbl}</div>', unsafe_allow_html=True)
            drop=wa[wa["ob"]<wa[ob_col]].copy(); drop["drop"]=drop["ob"]-drop[ob_col]; drop=drop.sort_values("drop")
            dd2=drop[["company","am","ob",ob_col,"drop"]].copy()
            dd2["drop_pct"]=drop.apply(lambda r:fmt_pct(r["drop"]/r[ob_col]) if r[ob_col]>0 else "—",axis=1)
            for c2_ in ["ob",ob_col,"drop"]: dd2[c2_]=dd2[c2_].apply(fmt_ccy)
            dd2.columns=["Company","AM","OB Now","OB Before","Drop","Drop %"]
            st.dataframe(dd2.reset_index(drop=True), use_container_width=True, height=280)

# ══════════════════════════════════════════════════════════════
# T · TEAM TRACKER
# ══════════════════════════════════════════════════════════════
with tabs[6]:
    st.markdown(section_header("Team Tracker", "Status · comments · follow-up dates per account"), unsafe_allow_html=True)
    t_am=st.selectbox("Account Manager",POD_AMS,key="t_am")
    t_mode=st.radio("View",["Focus View","Manager Overview"],horizontal=True,key="t_mode",label_visibility="collapsed")

    if t_mode=="Focus View":
        am_accts=fa[fa["am"]==t_am].copy()
        ov_cos_t=set(v2f[v2f["Stage"].isin({"overdue","npa"})]["buyer_lower"])
        npa_cos_t=set(v2f[v2f["Stage"]=="npa"]["buyer_lower"])
        for bname, mask, badge_v in [
            ("🔴 NPA",          am_accts["company"].str.lower().isin(npa_cos_t), "npa"),
            ("🟠 Overdue",      am_accts["company"].str.lower().isin(ov_cos_t-npa_cos_t), "overdue"),
            ("⏸ Suspended WA", am_accts["level2"]=="Suspended Workable", "suspended"),
            ("🟢 Active WA",   am_accts["level2"]=="Active Workable", "active"),
        ]:
            baccts=am_accts[mask]
            if baccts.empty: continue
            with st.expander(f"{bname}  ·  {len(baccts)} accounts"):
                for _,acct in baccts.iterrows():
                    kp=f"t_{t_am}_{acct['id']}"
                    c1,c2,c3,c4,c5=st.columns([3,2,3,2,2])
                    c1.markdown(f'<div style="padding:6px 0"><div style="font-family:IBM Plex Sans;font-weight:600;font-size:.84rem;color:#e6edf3">{acct["company"]}</div><div style="font-family:IBM Plex Mono;font-size:.68rem;color:#484f58">OB {fmt_ccy(acct["ob"])} · Fac {fmt_ccy(acct["total_fac"])}</div></div>', unsafe_allow_html=True)
                    c2.selectbox("Status",["—","In Progress","Contacted","Resolved","Escalated"],key=f"{kp}_s",label_visibility="collapsed")
                    c3.text_area("Comment","",key=f"{kp}_c",height=68,label_visibility="collapsed",placeholder="Add a note…")
                    c4.date_input("Last Contact",value=None,key=f"{kp}_lc",label_visibility="collapsed")
                    c5.date_input("Next Follow-up",value=None,key=f"{kp}_nf",label_visibility="collapsed")
                    st.markdown('<hr style="margin:2px 0;border-color:#21262d">', unsafe_allow_html=True)
    else:
        ov_cos_m=set(v2f[v2f["Stage"].isin({"overdue","npa"})]["buyer_lower"])
        rows=[{"AM":am,"Total":len(fa[fa["am"]==am]),
               "Active WA":len(fa[(fa["am"]==am)&(fa["level2"]=="Active Workable")]),
               "Suspended WA":len(fa[(fa["am"]==am)&(fa["level2"]=="Suspended Workable")]),
               "Overdue/NPA":len(fa[(fa["am"]==am)&fa["company"].str.lower().isin(ov_cos_m)]),
               "OB":fmt_ccy(fa[fa["am"]==am]["ob"].sum()),
               "WIRR":fmt_irr(wirr(fa[(fa["am"]==am)&fa["level2"].isin(["Active Workable","Suspended Workable"])]))}
              for am in POD_AMS]
        st.dataframe(pd.DataFrame(rows), use_container_width=True)

# ══════════════════════════════════════════════════════════════
# P · PEAK ANALYSIS
# ══════════════════════════════════════════════════════════════
with tabs[7]:
    if ob_pivot.empty:
        st.markdown(info_banner("📈 Upload Historical OB and Current OB files to enable Peak Analysis and OB Trend charts.","info"), unsafe_allow_html=True)
    else:
        st.markdown(section_header("Portfolio OB Trend"), unsafe_allow_html=True)
        c1,c2=st.columns(2)
        with c1: p_tw=st.radio("Window",["3M","6M","12M","All (Jul 2020)"],horizontal=True,key="ptw",label_visibility="collapsed")
        with c2: p_tm=st.radio("Mode",["Portfolio Total","Per AM"],horizontal=True,key="ptm",label_visibility="collapsed")
        tw_offsets={"3M":pd.DateOffset(months=3),"6M":pd.DateOffset(months=6),"12M":pd.DateOffset(years=1)}
        st_tr=pd.Timestamp("2020-07-01") if p_tw=="All (Jul 2020)" else today_ts-tw_offsets[p_tw]
        pod_ids_p=set(fa["id"])
        tr_cols=[c for c in ob_pivot.columns if c in pod_ids_p]
        tr_dates=[d for d in sorted_ob_keys if pd.Timestamp(d)>=st_tr and pd.Timestamp(d)<=today_ts]
        if tr_dates:
            td=ob_pivot[tr_cols].loc[tr_dates]
            fig=go.Figure()
            if p_tm=="Portfolio Total":
                fig.add_trace(go.Scatter(x=[str(d) for d in tr_dates], y=td.sum(axis=1).values/1e6,
                    mode="lines", name="Portfolio OB", line=dict(color="#f59e0b",width=2),
                    fill="tozeroy", fillcolor="rgba(245,158,11,.07)",
                    hovertemplate="<b>%{x}</b><br>$%{y:.2f}M<extra></extra>"))
            else:
                for am, color in zip(POD_AMS, AM_COLORS):
                    am_ids=[c for c in tr_cols if c in set(fa[fa["am"]==am]["id"])]
                    if not am_ids: continue
                    fig.add_trace(go.Scatter(x=[str(d) for d in tr_dates], y=td[am_ids].sum(axis=1).values/1e6,
                        mode="lines", name=am.split()[0], line=dict(color=color,width=1.5)))
            fig.update_layout(**plotly_layout(height=300, yaxis_tickprefix="$", yaxis_ticksuffix="M", hovermode="x unified"))
            st.plotly_chart(fig, use_container_width=True)
            st.markdown(info_banner("⚠ Step change at May 2026 reflects expanded account coverage in the Current OB file — not a real portfolio event.","warn"), unsafe_allow_html=True)

        st.markdown(section_header("Peak vs Today"), unsafe_allow_html=True)
        peak_mode=st.radio("Peak date",["Auto Peak","Custom Date"],horizontal=True,key="pm",label_visibility="collapsed")
        if peak_mode=="Custom Date":
            pk_key=closest_before(st.date_input("Select peak date",value=pd.Timestamp(sorted_ob_keys[-1]).date(),key="pd2"),sorted_ob_keys)
        else:
            pc2=[c for c in ob_pivot.columns if c in pod_ids_p]
            pk_key=ob_pivot[pc2].sum(axis=1).idxmax() if pc2 else (sorted_ob_keys[-1] if sorted_ob_keys else None)

        if pk_key:
            pc2=[c for c in ob_pivot.columns if c in pod_ids_p]
            ob_pk=ob_pivot[pc2].loc[pk_key] if pk_key in ob_pivot.index else pd.Series()
            tot_pk=ob_pk.sum(); tot_now=fa["ob"].sum(); net=tot_now-tot_pk
            c1,c2,c3=st.columns(3)
            c1.markdown(kpi_card(f"Peak OB  ({pk_key})", fmt_ccy(tot_pk), "All accounts at peak date", "muted"), unsafe_allow_html=True)
            c2.markdown(kpi_card("Today's OB", fmt_ccy(tot_now), "All accounts", "amber"), unsafe_allow_html=True)
            c3.markdown(kpi_card("Net Movement", fmt_ccy(net),
                fmt_pct(net/tot_pk if tot_pk else 0)+" from peak",
                "green" if net>=0 else "red"), unsafe_allow_html=True)

            chgs=[{"company":r["company"],"am":r["am"],"level2":r["level2"],
                   "ob_peak":float(ob_pk.get(r["id"],0)),"ob_today":r["ob"],"change":r["ob"]-float(ob_pk.get(r["id"],0))}
                  for _,r in fa.iterrows() if r["ob"]!=0 or float(ob_pk.get(r["id"],0))!=0]
            chgs.sort(key=lambda x: abs(x["change"]),reverse=True)
            t30=sorted(chgs[:30],key=lambda x:x["change"])
            if t30:
                st.markdown(section_header("Account Contribution to Change", "Top 30 by magnitude · green = grew · red = declined"), unsafe_allow_html=True)
                fig=go.Figure(go.Bar(
                    x=[x["change"]/1e6 for x in t30], y=[x["company"][:28] for x in t30],
                    orientation="h", marker_color=["#10b981" if x["change"]>=0 else "#ef4444" for x in t30],
                    marker_opacity=0.85, hovertemplate="<b>%{y}</b><br>%{x:+.2f}M<extra></extra>"))
                fig.update_layout(**plotly_layout(height=max(360,len(t30)*22), xaxis_tickprefix="$", xaxis_ticksuffix="M"))
                st.plotly_chart(fig, use_container_width=True)

            p_filt=st.selectbox("Filter table",["All","Workable","Declined","Grew","NWA Residual"],key="p_flt")
            cdf=pd.DataFrame(chgs)
            if p_filt=="Workable": cdf=cdf[cdf["level2"].isin(["Active Workable","Suspended Workable"])]
            elif p_filt=="Declined": cdf=cdf[cdf["change"]<0]
            elif p_filt=="Grew": cdf=cdf[cdf["change"]>0]
            elif p_filt=="NWA Residual": cdf=cdf[cdf["level2"].isin(["NWA","Workable_Over365"])&(cdf["ob_today"]>0)]
            cdf=cdf.copy(); cdf["change_pct"]=cdf.apply(lambda r:fmt_pct(r["change"]/r["ob_peak"]) if r["ob_peak"]!=0 else "—",axis=1)
            for c in ["ob_peak","ob_today","change"]: cdf[c]=cdf[c].apply(fmt_ccy)
            cdf.columns=["Company","AM","Category","OB at Peak","OB Today","Change","Change %"]
            with st.expander(f"Account Detail  ({len(cdf)} accounts)"):
                st.dataframe(cdf.reset_index(drop=True), use_container_width=True)

# ══════════════════════════════════════════════════════════════
# G · CP HEALTH
# ══════════════════════════════════════════════════════════════
with tabs[8]:
    st.markdown(section_header("CP Portfolio — Partner Health"), unsafe_allow_html=True)
    try:
        ss["up_mh"].seek(0); mh_raw=load_mh(ss["up_mh"])
        cp_mh=mh_raw[(mh_raw["Team"]=="CP")&(mh_raw["Partner"].str.strip()!="Direct")].copy()
        ss["up_v1"].seek(0); v1_raw=load_v1(ss["up_v1"])
        cp_rec=[]
        for _,row in cp_mh.iterrows():
            bid=row["Buyer_ID"]; v1r=v1_raw.loc[bid] if bid in v1_raw.index else pd.Series(dtype=object)
            fac=float(v1r.get("Facility_Size",0) or row["Facility_Size"] or 0)
            ovd=float(v1r.get("overdraft_limit",0) or row["Overdraft_Limit"] or 0)
            ob_v=v1r.get("Outstanding_Balance"); ob=float(ob_v if pd.notna(ob_v) else row["OB"] or 0)
            irr=float(v1r.get("Signed-up IRR",0) or row["Signed_up_IRR"] or 0)
            ld_raw=v1r.get("Last_Disbursed_Date") or row["Last_Disbursed_Date"]
            ld=pd.Timestamp(ld_raw) if pd.notna(ld_raw) else pd.NaT
            dld=int((today_ts-ld).days) if pd.notna(ld) else None
            tfac=fac+ovd
            cp_rec.append({"id":bid,"company":str(row["Buyer"]).strip(),"am":str(row.get("AM","") or "").strip(),
                "partner":str(row.get("Partner","") or "").strip(),"total_fac":tfac,"ob":ob,"irr":irr,
                "last_disb":ld,"days_last_disb":dld,"util_pct":min(ob/tfac,1) if tfac>0 else 0})
        cp_df=pd.DataFrame(cp_rec)
        tf=cp_df["total_fac"].sum()

        c1,c2,c3,c4=st.columns(4)
        c1.markdown(kpi_card("CP Accounts",  str(len(cp_df)), "Excl. Direct partner", "amber"), unsafe_allow_html=True)
        c2.markdown(kpi_card("CP OB",        fmt_ccy(cp_df["ob"].sum()), "Total outstanding", "amber"), unsafe_allow_html=True)
        c3.markdown(kpi_card("CP Facility",  fmt_ccy(tf), "Total facility size", "muted"), unsafe_allow_html=True)
        c4.markdown(kpi_card("CP Util %",    fmt_pct(cp_df["ob"].sum()/tf if tf else 0), "OB / Facility", "green"), unsafe_allow_html=True)

        st.markdown(section_header("OB & Utilization by Partner"), unsafe_allow_html=True)
        by_p=cp_df.groupby("partner").agg(cnt=("id","count"),ob=("ob","sum"),fac=("total_fac","sum")).sort_values("ob",ascending=False).head(20)
        fig=go.Figure()
        fig.add_trace(go.Bar(y=by_p.index,x=by_p["fac"]/1e6,name="Facility",marker_color="rgba(139,148,158,.25)",orientation="h"))
        fig.add_trace(go.Bar(y=by_p.index,x=by_p["ob"]/1e6, name="OB",     marker_color="#f59e0b",marker_opacity=0.85,orientation="h"))
        fig.update_layout(**plotly_layout(height=max(300,len(by_p)*30), barmode="overlay", xaxis_tickprefix="$", xaxis_ticksuffix="M"))
        st.plotly_chart(fig, use_container_width=True)

        ss["up_v2"].seek(0); v2_raw2=load_v2(ss["up_v2"])
        cp_cos=set(cp_mh["Buyer"].astype(str).str.lower()); v2_cp=v2_raw2[v2_raw2["buyer_lower"].isin(cp_cos)].copy()
        v2_cp["dpd2"]=pd.to_numeric(v2_cp["dpd"],errors="coerce").fillna(0)
        ov_cos_g=set(v2_cp[v2_cp["Stage"].isin(OPEN_ST)&(v2_cp["dpd2"]>7)]["buyer_lower"])
        act90=set(v2_cp[v2_cp["disbursed_date"].notna()&(v2_cp["disbursed_date"]>=(today_ts-timedelta(days=90)))]["buyer_lower"])
        cp_df["score"]=(
            (cp_df["util_pct"]*25).clip(0,25)+
            cp_df["company"].str.lower().apply(lambda c:0 if c in ov_cos_g else 25)+
            cp_df["days_last_disb"].apply(lambda d:25 if d is not None and d<=30 else 0)+
            cp_df["company"].str.lower().apply(lambda c:25 if c in act90 else 0)
        ).round().astype(int)

        st.markdown(section_header("Partner Health Scorecard", "Score /100 · Utilization 25 · Clean Book 25 · Recent Disb 25 · Active 90d 25"), unsafe_allow_html=True)
        for partner,grp in cp_df.groupby("partner"):
            avg=grp["score"].mean(); em="🟢" if avg>=75 else ("🟡" if avg>=50 else "🔴")
            ob_p=grp["ob"].sum(); fac_p=grp["total_fac"].sum()
            with st.expander(f"{em} {partner}  ·  {len(grp)} accounts  ·  Score {avg:.0f}/100  ·  OB {fmt_ccy(ob_p)}  ·  {fmt_pct(ob_p/fac_p if fac_p else 0)} util"):
                gd=grp.sort_values("score",ascending=False)[["company","am","total_fac","ob","util_pct","irr","score"]].copy()
                for c in ["total_fac","ob"]: gd[c]=gd[c].apply(fmt_ccy)
                gd["util_pct"]=gd["util_pct"].apply(fmt_pct); gd["irr"]=gd["irr"].apply(fmt_irr)
                gd["score"]=gd["score"].astype(str)+"/100"
                gd.columns=["Account","AM","Facility","OB","Util %","IRR","Health Score"]
                st.dataframe(gd.reset_index(drop=True), use_container_width=True)
    except Exception as e:
        st.error(f"CP Health error: {e}")
