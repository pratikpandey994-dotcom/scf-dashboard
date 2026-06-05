"""CP Pod · SCF Portfolio Dashboard — Streamlit Cloud edition"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import date, datetime, timedelta
import calendar
import io

st.set_page_config(page_title="CP Pod · SCF Portfolio", page_icon="📊", layout="wide")

# ── Constants ─────────────────────────────────────────────────────────────────
POD_AMS    = ["Nikhil Shetty","Darshan Hublikar","Deepsayan Dam","Ashitha Nair","Asif Ali"]
AM_COLORS  = ["#f59e0b","#10b981","#6366f1","#f97316","#94a3b8"]
AM_INIT    = {"Nikhil Shetty":"NS","Darshan Hublikar":"DH","Deepsayan Dam":"DD",
              "Ashitha Nair":"AN","Asif Ali":"AA"}
SETTLED    = {"closed","paid","received"}
OPEN_ST    = {"advanced","overdue","npa","partial"}
EXCL_ST    = {"partadvanced","processing","deposit_pending","pending_advance",
              "data_entry","verify_bank_details","hold"}
OB_CUTOFF  = pd.Timestamp("2026-05-01")

# ── Helpers ───────────────────────────────────────────────────────────────────
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

# ── Data loading from uploaded files ─────────────────────────────────────────
def read_excel(uploaded):
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
        broad = row["Broad_Account_Status"]
        v1u   = str(v1r.get("utilization_status","") or "").strip().lower()
        ld = v1r.get("Last_Disbursed_Date") or row["Last_Disbursed_Date"]
        fd = v1r.get("First_Disbursed_Date") or row["First_Disbursed_Date"]
        ld = pd.Timestamp(ld) if pd.notna(ld) else pd.NaT
        fd = pd.Timestamp(fd) if pd.notna(fd) else pd.NaT
        ds = int((today_ts - ld).days) if pd.notna(ld) else None
        if   broad != "Workable":         l2 = "NWA"
        elif ds is None or ds > 365:      l2 = "Workable_Over365"
        elif v1u == "active":             l2 = "Active Workable"
        else:                             l2 = "Suspended Workable"
        fac = float(v1r.get("Facility_Size",0) or row["Facility_Size"] or 0)
        ovd = float(v1r.get("overdraft_limit",0) or row["Overdraft_Limit"] or 0)
        ob_v = v1r.get("Outstanding_Balance")
        ob   = float(ob_v if pd.notna(ob_v) else row["OB"] or 0)
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

# ── Upload screen ─────────────────────────────────────────────────────────────
ss = st.session_state

def show_upload():
    st.markdown("## CP POD · **SCF Portfolio Dashboard**")
    st.markdown("Upload your weekly files to launch the dashboard.")
    st.markdown("---")

    c1, c2, c3 = st.columns(3)
    with c1:
        ss["up_v1"]  = st.file_uploader("📋 View 1 — Accounts",       type=["xlsx","xls"], key="fu_v1",
            help="Weekly · facility, OB, utilization, AM")
        ss["up_v2"]  = st.file_uploader("🧾 View 2 — Invoices",       type=["xlsx","xls"], key="fu_v2",
            help="Weekly · stages, DPD, origination, settlement")
        ss["up_mh"]  = st.file_uploader("🗂️ Master Handover",          type=["xlsx","xls"], key="fu_mh",
            help="Buyer_ID, AM, Account_Status, Broad_Account_Status")
    with c2:
        ss["up_obhist"]  = st.file_uploader("📈 Historical OB (File 5)", type=["xlsx","xls"], key="fu_obhist",
            help="Jun 2020 – Apr 2026 · importer_user_id, ob_date, ob")
        ss["up_obcurr"]  = st.file_uploader("➕ Current OB File",        type=["xlsx","xls"], key="fu_obcurr",
            help="May 2026 onwards · importer_user_id, ob_date, ob")
    with c3:
        st.markdown("#### Required files")
        req = {"View 1": ss.get("up_v1"), "View 2": ss.get("up_v2"), "Master Handover": ss.get("up_mh")}
        for name, f in req.items():
            st.markdown(f"{'✅' if f else '⬜'} **{name}**")
        st.markdown("#### Optional (enables OB trend & peak analysis)")
        for name, f in [("Historical OB", ss.get("up_obhist")), ("Current OB", ss.get("up_obcurr"))]:
            st.markdown(f"{'✅' if f else '⬜'} {name}")

    st.markdown("---")
    col_date, col_btn = st.columns([2, 3])
    with col_date:
        ss["today_in"] = st.date_input("Today's Date", value=date.today(), key="date_sel")
    with col_btn:
        st.markdown("")
        ready = all([ss.get("up_v1"), ss.get("up_v2"), ss.get("up_mh")])
        if st.button("LAUNCH DASHBOARD →", disabled=not ready, type="primary", use_container_width=True):
            with st.spinner("Processing data — this takes ~30 seconds on first load…"):
                try:
                    v1_df   = load_v1(ss["up_v1"])
                    v2_df   = load_v2(ss["up_v2"])
                    mh_df   = load_mh(ss["up_mh"])
                    obh_df  = load_ob(ss["up_obhist"], lambda d: d < OB_CUTOFF) if ss.get("up_obhist") else None
                    obc_df  = load_ob(ss["up_obcurr"], lambda d: d >= OB_CUTOFF) if ss.get("up_obcurr") else None
                    today_ts = pd.Timestamp(ss["today_in"])
                    pod, v2p, ob_pivot = process_data(v1_df, mh_df, v2_df, obh_df, obc_df, today_ts)
                    ss["pod"]      = pod
                    ss["v2p"]      = v2p
                    ss["ob_pivot"] = ob_pivot
                    ss["today_ts"] = today_ts
                    ss["loaded"]   = True
                    st.rerun()
                except Exception as e:
                    st.error(f"Error loading data: {e}")
                    import traceback; st.code(traceback.format_exc())

# ── Check session ─────────────────────────────────────────────────────────────
if not ss.get("loaded"):
    show_upload()
    st.stop()

# ── Main app ──────────────────────────────────────────────────────────────────
pod      = ss["pod"]
v2p_all  = ss["v2p"]
ob_pivot = ss["ob_pivot"]
today_ts = ss["today_ts"]
sorted_ob_keys = sorted(ob_pivot.index) if not ob_pivot.empty else []

# Header row
c1, c2, c3 = st.columns([2, 5, 2])
with c1: st.markdown(f"### CP POD · **SCF**")
with c2:
    am_opts = ["All"] + POD_AMS
    am_lbls = ["All","NS","DH","DD","AN","AA"]
    gam_i = st.radio("AM", range(len(am_opts)), format_func=lambda i: am_lbls[i],
                     horizontal=True, label_visibility="collapsed", key="gam")
    global_am = am_opts[gam_i]
with c3:
    if st.button("↑ Re-upload", use_container_width=True):
        ss["loaded"] = False; st.rerun()

st.markdown("---")

fa  = pod  if global_am == "All" else pod[pod["am"] == global_am]
v2f = v2p_all if global_am == "All" else v2p_all[v2p_all["am"] == global_am]

tabs = st.tabs(["F · Snapshot","A · Portfolio","B · Team","C · Health",
                "D · Actions","H · Account Pulse","T · Tracker","P · Peak","G · CP Health"])

# ══════════════════════════════════════════════════════════
# VIEW F — EXECUTIVE SNAPSHOT
# ══════════════════════════════════════════════════════════
with tabs[0]:
    tgt     = fa[fa["level2"].isin(["Active Workable","Suspended Workable"])]
    tot_ob  = tgt["ob"].sum(); tot_fac = tgt["total_fac"].sum()
    open_inv = v2f[v2f["Stage"].isin(OPEN_ST)]
    ov_inv  = open_inv[(open_inv["dpd"]>7)&(open_inv["dpd"]<=90)]
    npa_inv = open_inv[open_inv["dpd"]>90]
    ov_ob   = ov_inv["Outstanding"].sum(); npa_ob = npa_inv["Outstanding"].sum()
    clean_ob = max(0, tot_ob - ov_ob - npa_ob)

    st.markdown("##### Portfolio Scale")
    c1,c2,c3,c4 = st.columns(4)
    c1.metric("Total OB",        fmt_ccy(tot_ob),  f"{len(tgt)} WA accounts")
    c2.metric("Total Facility",  fmt_ccy(tot_fac), "Facility + Overdraft")
    c3.metric("Util %",          fmt_pct(tot_ob/tot_fac if tot_fac else 0))
    c4.metric("Total Accounts",  len(fa), f"{len(fa[fa['broad']=='Workable'])} WA · {len(fa[fa['level2']=='NWA'])} NWA")

    st.markdown("##### Account Health")
    h1,h2,h3,h4,h5,h6 = st.columns(6)
    for col, key, label in [
        (h1,"Active Workable","Active WA"),
        (h2,"Suspended Workable","Suspended WA"),
        (h3,"Workable_Over365","WA >365d"),
        (h4,"NWA","Non-Workable"),
    ]:
        sub = fa[fa["level2"]==key]
        col.metric(label, len(sub), fmt_ccy(sub["ob"].sum())+" OB")
    nw = fa[fa["level2"]=="NWA"]
    h5.metric("NWA >365d", len(nw[nw["days_since"].fillna(999)>365]))
    h6.metric("NWA ≤365d", len(nw[nw["days_since"].fillna(999)<=365]))

    st.markdown("##### Yield"); c1,c2,c3 = st.columns(3)
    aw = fa[fa["level2"]=="Active Workable"]; sw = fa[fa["level2"]=="Suspended Workable"]
    c1.metric("Portfolio WIRR",    fmt_irr(wirr(tgt)))
    c2.metric("Active WA WIRR",    fmt_irr(wirr(aw)))
    c3.metric("Suspended WA WIRR", fmt_irr(wirr(sw)))

    st.markdown("##### Risk"); c1,c2,c3 = st.columns(3)
    c1.metric("Overdue (DPD 8–90)", fmt_ccy(ov_ob),   f"{len(ov_inv)} invoices",  delta_color="inverse")
    c2.metric("NPA (DPD >90)",      fmt_ccy(npa_ob),  f"{len(npa_inv)} invoices", delta_color="inverse")
    c3.metric("Clean OB",           fmt_ccy(clean_ob), fmt_pct(clean_ob/tot_ob if tot_ob else 0))

# ══════════════════════════════════════════════════════════
# VIEW A — PORTFOLIO
# ══════════════════════════════════════════════════════════
with tabs[1]:
    tgt  = fa[fa["level2"].isin(["Active Workable","Suspended Workable"])]
    aw   = fa[fa["level2"]=="Active Workable"]; sw  = fa[fa["level2"]=="Suspended Workable"]
    nwa  = fa[fa["level2"]=="NWA"];             o365 = fa[fa["level2"]=="Workable_Over365"]
    open_inv = v2f[v2f["Stage"].isin(OPEN_ST)]
    ov_ob  = open_inv[(open_inv["dpd"]>7)&(open_inv["dpd"]<=90)]["Outstanding"].sum()
    npa_ob = open_inv[open_inv["dpd"]>90]["Outstanding"].sum()
    tot_ob = tgt["ob"].sum(); clean_ob = max(0, tot_ob - ov_ob - npa_ob)
    ov_cos  = set(open_inv[(open_inv["dpd"]>7)&(open_inv["dpd"]<=90)]["buyer_lower"])
    npa_cos = set(open_inv[open_inv["dpd"]>90]["buyer_lower"])

    st.markdown("##### Portfolio Quality")
    c1,c2,c3 = st.columns(3)
    c1.metric("Clean OB",             fmt_ccy(clean_ob), fmt_pct(clean_ob/tot_ob if tot_ob else 0))
    c2.metric("Overdue OB (DPD 8–90)",fmt_ccy(ov_ob),   delta_color="inverse")
    c3.metric("NPA OB (DPD >90)",     fmt_ccy(npa_ob),  delta_color="inverse")

    pq_filter = st.selectbox("Filter", ["All","Clean","Overdue","NPA"], key="pq_f")
    pq = tgt.copy()
    pq["cat"] = pq["company"].str.lower().apply(
        lambda c: "npa" if c in npa_cos else ("overdue" if c in ov_cos else "clean"))
    if pq_filter != "All": pq = pq[pq["cat"] == pq_filter.lower()]
    pq = pq.sort_values("ob", ascending=False)
    pq["util_pct"] = pq.apply(lambda r: min(r["ob"]/r["total_fac"],1) if r["total_fac"]>0 else 0, axis=1)

    cl, cr = st.columns([1,2])
    with cl:
        fig = go.Figure(go.Pie(labels=["Clean","Overdue","NPA"],
            values=[clean_ob/1e6, ov_ob/1e6, npa_ob/1e6], hole=0.6,
            marker_colors=["#10b981","#f97316","#ef4444"]))
        fig.update_layout(paper_bgcolor="#0f172a", plot_bgcolor="#0f172a", font_color="#94a3b8",
            height=260, margin=dict(l=0,r=0,t=0,b=0), showlegend=True,
            legend=dict(orientation="h", y=-0.15))
        st.plotly_chart(fig, use_container_width=True)
    with cr:
        d = pq[["company","am","cat","total_fac","ob","util_pct"]].copy()
        d.columns = ["Company","AM","Status","Facility","OB","Util"]
        d["Facility"] = d["Facility"].apply(fmt_ccy); d["OB"] = d["OB"].apply(fmt_ccy)
        d["Util"] = d["Util"].apply(fmt_pct)
        st.dataframe(d.reset_index(drop=True), use_container_width=True, height=260)

    st.markdown("##### Weighted IRR")
    thresh = st.number_input("OB Threshold ≥ $", value=0, min_value=0, step=1000, key="a_thresh")
    c1,c2,c3 = st.columns(3)
    c1.metric("Portfolio WIRR",    fmt_irr(wirr(tgt,"ob","irr",thresh)))
    c2.metric("Active WA WIRR",    fmt_irr(wirr(aw,"ob","irr",thresh)))
    c3.metric("Suspended WA WIRR", fmt_irr(wirr(sw,"ob","irr",thresh)))

    st.markdown("##### Targetable Portfolio")
    pc = st.columns(4)
    for (lbl, arr, tag), col in zip([
        ("🟢 Active WA",aw,"IN TARGET"),("🟠 Suspended WA",sw,"IN TARGET"),
        ("⏸ WA >365d",o365,"EXCL."),("⛔ NWA",nwa,"NWA")], pc):
        ob = arr["ob"].sum(); fac = arr["total_fac"].sum()
        col.metric(f"{lbl} [{tag}]", len(arr), f"{fmt_ccy(ob)} OB · {fmt_pct(ob/fac if fac else 0)} util")

    st.markdown("##### Origination vs Repayment")
    ovr_win = st.radio("Window",["MTD","QTD"], horizontal=True, key="ovr_win")
    s_ovr, e_ovr = get_window("mtd" if ovr_win=="MTD" else "qtd", today_ts)
    ao = {a:0 for a in POD_AMS+["Team"]}; ar = {a:0 for a in POD_AMS+["Team"]}
    for _, inv in v2f.iterrows():
        if inv["Stage"] in EXCL_ST or inv["am"] not in POD_AMS: continue
        if pd.notna(inv["disbursed_date"]) and in_win(inv["disbursed_date"], s_ovr, e_ovr):
            ao[inv["am"]] += inv["Origination"]; ao["Team"] += inv["Origination"]
        if inv["Stage"] in SETTLED|{"partial"} and pd.notna(inv["settlement_date"]) and in_win(inv["settlement_date"], s_ovr, e_ovr):
            r = max(0, inv["Origination"]-inv["Outstanding"])
            ar[inv["am"]] += r; ar["Team"] += r
    short = [a.split()[0] for a in POD_AMS]; keys = [*POD_AMS,"Team"]; lbls = [*short,"Team"]
    nets = [(ao[k]-ar[k])/1e6 for k in keys]
    fig = go.Figure()
    fig.add_trace(go.Bar(x=lbls, y=[ao[k]/1e6 for k in keys], name="Originated", marker_color="rgba(99,102,241,.75)"))
    fig.add_trace(go.Bar(x=lbls, y=[ar[k]/1e6 for k in keys], name="Repaid",     marker_color="rgba(16,185,129,.65)"))
    fig.add_trace(go.Bar(x=lbls, y=nets, name="Net",
        marker_color=["rgba(245,158,11,.8)" if v>=0 else "rgba(239,68,68,.8)" for v in nets]))
    fig.update_layout(paper_bgcolor="#0f172a",plot_bgcolor="#0f172a",font_color="#94a3b8",
        height=240,barmode="group",yaxis_tickprefix="$",yaxis_ticksuffix="M",
        margin=dict(l=0,r=0,t=0,b=0))
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("##### Collections Tracker")
    c_am  = st.selectbox("AM",["All"]+POD_AMS, key="c_am",
                format_func=lambda x: "All" if x=="All" else x.split()[0])
    c_win = st.radio("Window",["Curr Wk","Next Wk","Curr Mo","Next Mo"], horizontal=True, key="c_win")
    cw_map = {"Curr Wk":"cw","Next Wk":"nw","Curr Mo":"cm","Next Mo":"nm"}
    ci = v2f if c_am=="All" else v2f[v2f["am"]==c_am]
    ms = pd.Timestamp(today_ts.year, today_ts.month, 1)
    recv = ci[ci["Stage"].isin(SETTLED) & ci["settlement_date"].notna() &
              ci["settlement_date"].apply(lambda d: in_win(d, ms, today_ts))
              ].apply(lambda r: max(0, r["Origination"]-r["Outstanding"]), axis=1).sum()
    ws, we = get_window(cw_map[c_win], today_ts)
    tr_inv = ci[ci["Stage"].isin({"advanced","partial"}) & ci["due_date_of_invoice"].notna() &
                ci["due_date_of_invoice"].apply(lambda d: in_win(d, ws, we))]
    rec = ci[ci["Stage"].isin({"overdue","npa"})].apply(
        lambda r: max(0, r["Origination"]-r["Outstanding"]), axis=1).sum()
    c1,c2,c3 = st.columns(3)
    c1.metric("✅ Received MTD", fmt_ccy(recv))
    c2.metric("⏳ To Receive",   fmt_ccy(tr_inv["Outstanding"].sum()))
    c3.metric("⚠ Recovery",      fmt_ccy(rec))
    by_co = tr_inv.groupby("Buyer").agg(
        AM=("am","first"), Invoices=("Invoice ID","count"),
        Total=("Outstanding","sum"),
        MinDue=("due_date_of_invoice","min"), MaxDue=("due_date_of_invoice","max")
    ).sort_values("Total", ascending=False)
    by_co["Total"]     = by_co["Total"].apply(fmt_ccy)
    by_co["Due Range"] = by_co.apply(
        lambda r: fmt_date(r["MinDue"]) + ("" if r["MinDue"]==r["MaxDue"] else " → "+fmt_date(r["MaxDue"])), axis=1)
    with st.expander(f"To Receive Detail ({len(by_co)})"):
        st.dataframe(by_co[["AM","Invoices","Total","Due Range"]].reset_index(), use_container_width=True)

# ══════════════════════════════════════════════════════════
# VIEW B — TEAM PERFORMANCE
# ══════════════════════════════════════════════════════════
with tabs[2]:
    st.markdown("##### AM Scorecards")
    ams_show = [global_am] if global_am != "All" else POD_AMS
    ms = pd.Timestamp(today_ts.year, today_ts.month, 1)
    bcols = st.columns(len(ams_show))
    for am, col in zip(ams_show, bcols):
        accts = fa[fa["am"]==am]
        aw_ = accts[accts["level2"]=="Active Workable"]
        sw_ = accts[accts["level2"]=="Suspended Workable"]
        ai  = v2f[v2f["am"]==am]
        orig_mtd = ai[ai["disbursed_date"].notna() & ai["disbursed_date"].apply(lambda d: in_win(d,ms,today_ts))]["Origination"].sum()
        rep_mtd  = ai[ai["Stage"].isin(SETTLED|{"partial"}) & ai["settlement_date"].notna() &
                      ai["settlement_date"].apply(lambda d: in_win(d,ms,today_ts))
                      ].apply(lambda r: max(0,r["Origination"]-r["Outstanding"]), axis=1).sum()
        early_mtd = ai[ai["Stage"].isin(SETTLED) & ai["settlement_date"].notna() &
                       ai["due_date_of_invoice"].notna() & (ai["settlement_date"]<ai["due_date_of_invoice"]) &
                       ai["settlement_date"].apply(lambda d: in_win(d,ms,today_ts))]["Origination"].sum()
        with col:
            st.markdown(f"**{AM_INIT.get(am,am[:2])} — {am.split()[0]}** ({len(accts)})")
            st.caption(f"AW: {len(aw_)} · SW: {len(sw_)}")
            st.metric("Active WA OB",  fmt_ccy(aw_["ob"].sum()))
            st.metric("Susp WA OB",    fmt_ccy(sw_["ob"].sum()))
            st.metric("MTD Originated",fmt_ccy(orig_mtd))
            st.metric("MTD Repaid",    fmt_ccy(rep_mtd))
            st.metric("MTD Early",     fmt_ccy(early_mtd))
            st.metric("WIRR",          fmt_irr(wirr(accts[accts["level2"].isin(["Active Workable","Suspended Workable"])])))

    st.markdown("---\n##### AM Status Distribution")
    aw_c,sw_c,o_c,n_c = [],[],[],[]
    for am in POD_AMS:
        a = fa[fa["am"]==am]
        aw_c.append(len(a[a["level2"]=="Active Workable"]))
        sw_c.append(len(a[a["level2"]=="Suspended Workable"]))
        o_c.append(len(a[a["level2"]=="Workable_Over365"]))
        n_c.append(len(a[a["level2"]=="NWA"]))
    fig = go.Figure()
    for data, name, color in [
        (aw_c,"Active Workable","rgba(16,185,129,.75)"),
        (sw_c,"Suspended WA",   "rgba(249,115,22,.65)"),
        (o_c, ">365d",          "rgba(71,85,105,.5)"),
        (n_c, "NWA",            "rgba(71,85,105,.3)")]:
        fig.add_trace(go.Bar(x=[a.split()[0] for a in POD_AMS], y=data, name=name, marker_color=color))
    fig.update_layout(barmode="stack",paper_bgcolor="#0f172a",plot_bgcolor="#0f172a",
        font_color="#94a3b8",height=260,margin=dict(l=0,r=0,t=0,b=0))
    st.plotly_chart(fig, use_container_width=True)

# ══════════════════════════════════════════════════════════
# VIEW C — BOOK HEALTH
# ══════════════════════════════════════════════════════════
with tabs[3]:
    wa = fa[fa["level2"].isin(["Active Workable","Suspended Workable"])].copy()
    wa["util"]   = wa.apply(lambda r: min(r["ob"]/r["total_fac"],1) if r["total_fac"]>0 else 0, axis=1)
    wa["bucket"] = wa["util"].apply(lambda u: "Zero" if u<=0 else ("Low" if u<=0.4 else ("Medium" if u<=0.74 else "High")))
    br = {"Zero":"0%","Low":"1–40%","Medium":"41–74%","High":"75–100%"}

    st.markdown("##### Utilization Buckets")
    for bk, col in zip(["Zero","Low","Medium","High"], st.columns(4)):
        sub = wa[wa["bucket"]==bk]; col.metric(f"{bk} ({br[bk]})", len(sub), fmt_ccy(sub["ob"].sum()))

    bsel = st.selectbox("Detail View",["All","Zero","Low","Medium","High"], key="bsel")
    bd = (wa if bsel=="All" else wa[wa["bucket"]==bsel]).sort_values("ob", ascending=False).copy()
    bd["Facility"] = bd["total_fac"].apply(fmt_ccy); bd["OB"] = bd["ob"].apply(fmt_ccy)
    bd["Util %"]   = bd["util"].apply(fmt_pct)
    st.dataframe(bd[["company","am","level2","Facility","OB","Util %"]].rename(
        columns={"company":"Company","am":"AM","level2":"Status"}).reset_index(drop=True),
        use_container_width=True, height=280)

    st.markdown("##### Overdue & NPA Detail")
    open_inv = v2f[v2f["Stage"].isin(OPEN_ST)]
    for lbl, inv_df in [("Overdue (DPD 8–90)", open_inv[(open_inv["dpd"]>7)&(open_inv["dpd"]<=90)]),
                         ("NPA (DPD >90)",      open_inv[open_inv["dpd"]>90])]:
        tot = inv_df["Outstanding"].sum()
        st.metric(f"{lbl}", fmt_ccy(tot), f"{len(inv_df)} invoices", delta_color="inverse")
        d = inv_df.copy()
        d["Recovered"] = (d["Origination"]-d["Outstanding"]).clip(lower=0).apply(fmt_ccy)
        d["Origination"] = d["Origination"].apply(fmt_ccy); d["Outstanding"] = d["Outstanding"].apply(fmt_ccy)
        with st.expander(f"{lbl} Detail ({len(inv_df)})"):
            st.dataframe(d[["Buyer","am","Invoice ID","Stage","Origination","Outstanding","dpd","Recovered"]].reset_index(drop=True), use_container_width=True)

    st.markdown("##### Days Since Last Disbursement")
    db  = st.selectbox("Bucket",["All","0-30","31-60","61-90","91-120","121-150","151-180","180+"], key="dsld")
    wda = fa[fa["level2"].isin(["Active Workable","Suspended Workable","Workable_Over365"])].copy()
    if db != "All":
        if db == "180+": wda = wda[wda["days_since"].notna()&(wda["days_since"]>=180)]
        else:
            lo,hi = map(int, db.split("-"))
            wda = wda[wda["days_since"].notna()&(wda["days_since"]>=lo)&(wda["days_since"]<=hi)]
    wda = wda.sort_values("days_since", ascending=False)
    d = wda[["company","am","level2","last_disb","days_since"]].copy()
    d["last_disb"] = d["last_disb"].apply(fmt_date); d.columns = ["Company","AM","Status","Last Disbursed","Days Since"]
    st.dataframe(d.reset_index(drop=True), use_container_width=True, height=350)

# ══════════════════════════════════════════════════════════
# VIEW D — ACTION BOARD
# ══════════════════════════════════════════════════════════
with tabs[4]:
    st.markdown("##### Declining Accounts")
    dw = st.radio("Window",["MTD","QTD"], horizontal=True, key="dw")
    sd, ed = get_window("mtd" if dw=="MTD" else "qtd", today_ts)
    amap = {}
    for _, inv in v2f.iterrows():
        if inv["level2"] in ["NWA","Workable_Over365"]: continue
        co = inv["Buyer"]
        if co not in amap: amap[co] = {"am":inv["am"],"level2":inv["level2"],"orig":0,"rep":0}
        if pd.notna(inv["disbursed_date"]) and in_win(inv["disbursed_date"],sd,ed):
            amap[co]["orig"] += inv["Origination"]
        if inv["Stage"] in SETTLED|{"partial"} and pd.notna(inv["settlement_date"]) and in_win(inv["settlement_date"],sd,ed):
            amap[co]["rep"] += max(0,inv["Origination"]-inv["Outstanding"])
    decl = [(co,v) for co,v in amap.items() if v["rep"]>v["orig"]]; decl.sort(key=lambda x:x[1]["orig"]-x[1]["rep"])
    if decl:
        t15 = decl[:15]
        fig = go.Figure(go.Bar(x=[v["orig"]-v["rep"] for _,v in t15], y=[co[:22] for co,_ in t15],
            orientation="h", marker_color=["rgba(239,68,68,.75)" if v["orig"]-v["rep"]<0 else "rgba(16,185,129,.75)" for _,v in t15]))
        fig.update_layout(paper_bgcolor="#0f172a",plot_bgcolor="#0f172a",font_color="#94a3b8",
            height=350,xaxis_tickprefix="$",margin=dict(l=0,r=0,t=0,b=0))
        st.plotly_chart(fig, use_container_width=True)
    dd = pd.DataFrame([{"Company":co,"AM":v["am"],"Originated":fmt_ccy(v["orig"]),"Repaid":fmt_ccy(v["rep"]),"Net":fmt_ccy(v["orig"]-v["rep"]),"Status":v["level2"]} for co,v in decl])
    with st.expander(f"Declining ({len(decl)})"):
        st.dataframe(dd.reset_index(drop=True) if not dd.empty else pd.DataFrame(), use_container_width=True)

    st.markdown("##### High Opportunity")
    ow = st.radio("Due In",["Curr Wk","Next Wk","Curr Mo","Next Mo"], horizontal=True, key="ow")
    ow_map = {"Curr Wk":"cw","Next Wk":"nw","Curr Mo":"cm","Next Mo":"nm"}
    ws,we = get_window(ow_map[ow], today_ts)
    dbc = {}
    for _,inv in v2f.iterrows():
        if inv["Stage"] not in {"advanced","partial"}: continue
        if pd.notna(inv["due_date_of_invoice"]) and in_win(inv["due_date_of_invoice"],ws,we):
            dbc[inv["buyer_lower"]] = dbc.get(inv["buyer_lower"],0) + inv["Outstanding"]
    wo = fa[fa["level2"].isin(["Active Workable","Suspended Workable"])].copy()
    wo["headroom"] = (wo["total_fac"]-wo["ob"]).clip(lower=0)
    wo["due"]  = wo["company"].str.lower().map(dbc).fillna(0)
    wo["opp"]  = wo["headroom"] + wo["due"]
    wo = wo[wo["opp"]>0].sort_values("opp", ascending=False)
    od = wo[["company","am","headroom","due","opp","level2"]].copy()
    od["headroom"] = od["headroom"].apply(fmt_ccy); od["due"] = od["due"].apply(fmt_ccy); od["opp"] = od["opp"].apply(fmt_ccy)
    od.columns = ["Company","AM","Headroom","Due Repayments","Total Opportunity","Status"]
    with st.expander(f"High Opportunity ({len(wo)})"):
        st.dataframe(od.reset_index(drop=True), use_container_width=True)

    st.markdown("##### Early Repayment")
    early = v2f[v2f["Stage"].isin(SETTLED)&v2f["settlement_date"].notna()&
                v2f["due_date_of_invoice"].notna()&(v2f["settlement_date"]<v2f["due_date_of_invoice"])].copy()
    early["days_early"] = (early["due_date_of_invoice"]-early["settlement_date"]).dt.days
    early = early.sort_values("days_early", ascending=False)
    ed2 = early[["Buyer","am","Invoice ID","Origination","settlement_date","due_date_of_invoice","days_early"]].copy()
    ed2["Origination"]=ed2["Origination"].apply(fmt_ccy); ed2["settlement_date"]=ed2["settlement_date"].apply(fmt_date); ed2["due_date_of_invoice"]=ed2["due_date_of_invoice"].apply(fmt_date)
    ed2.columns=["Company","AM","Invoice ID","Origination","Settlement","Due Date","Days Early"]
    with st.expander(f"Early Repayments ({len(early)})"):
        st.dataframe(ed2.reset_index(drop=True), use_container_width=True)

    st.markdown("##### Reactivation Focus — Suspended · ≥180 days dormant")
    react = fa[(fa["broad"]=="Workable")&(fa["v1_util"]=="suspended")&fa["days_since"].notna()&(fa["days_since"]>=180)].sort_values("peak_ob",ascending=False).copy()
    rd = react[["company","am","total_fac","ob","peak_ob","avg_ob","days_since"]].copy()
    for c in ["total_fac","ob","peak_ob","avg_ob"]: rd[c] = rd[c].apply(fmt_ccy)
    rd.columns=["Company","AM","Total Facility","Current OB","Peak OB","Avg OB","Days Since Last Disb"]
    with st.expander(f"Reactivation ({len(react)})"):
        st.dataframe(rd.reset_index(drop=True), use_container_width=True)

# ══════════════════════════════════════════════════════════
# VIEW H — ACCOUNT PULSE
# ══════════════════════════════════════════════════════════
with tabs[5]:
    wa = fa[fa["level2"].isin(["Active Workable","Suspended Workable"])].copy()
    wa["util"] = wa.apply(lambda r: min(r["ob"]/r["total_fac"],1) if r["total_fac"]>0 else 0, axis=1)
    ob30_map, ob90_map = {}, {}
    if not ob_pivot.empty:
        k30 = closest_before((today_ts-timedelta(days=30)).date(), sorted_ob_keys)
        k90 = closest_before((today_ts-timedelta(days=90)).date(), sorted_ob_keys)
        if k30 and k30 in ob_pivot.index: ob30_map = ob_pivot.loc[k30].to_dict()
        if k90 and k90 in ob_pivot.index: ob90_map = ob_pivot.loc[k90].to_dict()
    wa["ob30"] = wa["id"].map(ob30_map).fillna(0)
    wa["ob90"] = wa["id"].map(ob90_map).fillna(0)
    wa["chg30"] = wa["ob"] - wa["ob30"]

    st.markdown("##### Workable Accounts")
    c1,c2,c3 = st.columns([2,3,3])
    with c1: h_sort = st.radio("Sort",["Facility","OB","Util %"], horizontal=True, key="hs")
    with c2: h_n = st.radio("Show",["Top 10","Top 25","Top 50","All","Bot 50"], horizontal=True, key="hn")
    with c3: h_rw = st.radio("Highlight Due",["None","This Week","This Month","Next Month"], horizontal=True, key="hrw")
    sort_c = {"Facility":"total_fac","OB":"ob","Util %":"util"}[h_sort]
    ws_ = wa.sort_values(sort_c, ascending=False)
    w_disp = ws_ if h_n=="All" else (ws_.tail(50) if h_n.startswith("Bot") else ws_.head(int(h_n.split()[-1])))
    rw_map = {"None":None,"This Week":"cw","This Month":"cm","Next Month":"nm"}
    due_hl = {}
    if rw_map[h_rw]:
        ws2, we2 = get_window(rw_map[h_rw], today_ts)
        for _,inv in v2f.iterrows():
            if inv["Stage"] not in {"advanced","partial"}: continue
            if pd.notna(inv["due_date_of_invoice"]) and in_win(inv["due_date_of_invoice"],ws2,we2):
                due_hl[inv["buyer_lower"]] = due_hl.get(inv["buyer_lower"],0) + inv["Outstanding"]
    w_disp = w_disp.copy(); w_disp["due"] = w_disp["company"].str.lower().map(due_hl).fillna(0)
    wd = w_disp[["company","am","level2","total_fac","ob","util","chg30","due","last_disb","peak_ob","avg_ob"]].copy()
    for c in ["total_fac","ob","peak_ob","avg_ob"]: wd[c] = wd[c].apply(fmt_ccy)
    wd["util"]=wd["util"].apply(fmt_pct); wd["chg30"]=wd["chg30"].apply(lambda v:("+" if v>=0 else "")+fmt_ccy(v))
    wd["due"]=wd["due"].apply(lambda v: fmt_ccy(v) if v>0 else "—"); wd["last_disb"]=wd["last_disb"].apply(fmt_date)
    wd.columns=["Company","AM","Status","Total Facility","OB","Util %","OB Chg 30d","Due (Sel)","Last Disb","Peak OB","Avg OB"]
    st.dataframe(wd.reset_index(drop=True), use_container_width=True, height=400)

    st.markdown("##### About to Go Inactive — Active WA · ≥120 days")
    inact = wa[(wa["level2"]=="Active Workable")&wa["days_since"].notna()&(wa["days_since"]>=120)].sort_values("days_since",ascending=False)
    c1,c2,c3 = st.columns(3)
    c1.metric("At Risk",len(inact)); c2.metric("OB at Risk",fmt_ccy(inact["ob"].sum())); c3.metric("Facility at Risk",fmt_ccy(inact["total_fac"].sum()))
    ind = inact[["company","am","total_fac","ob","util","last_disb","days_since","peak_ob"]].copy()
    for c in ["total_fac","ob","peak_ob"]: ind[c]=ind[c].apply(fmt_ccy)
    ind["util"]=ind["util"].apply(fmt_pct); ind["last_disb"]=ind["last_disb"].apply(fmt_date)
    ind.columns=["Company","AM","Facility","OB","Util %","Last Disb","Days Since","Peak OB"]
    with st.expander(f"Inactive Risk ({len(inact)})"):
        st.dataframe(ind.reset_index(drop=True), use_container_width=True)

    st.markdown("##### Headroom Opportunity")
    hr = wa[wa["days_since"].fillna(0)<120].copy()
    hr["headroom"]=(hr["total_fac"]-hr["ob"]).clip(lower=0); hr["peak_gap"]=(hr["peak_ob"]-hr["ob"]).clip(lower=0)
    hr = hr[hr["headroom"]>0].sort_values("headroom",ascending=False)
    hrd = hr[["company","am","total_fac","ob","util","headroom","peak_ob","peak_gap"]].copy()
    for c in ["total_fac","ob","peak_ob"]: hrd[c]=hrd[c].apply(fmt_ccy)
    hrd["util"]=hrd["util"].apply(fmt_pct); hrd["headroom"]=hrd["headroom"].apply(fmt_ccy); hrd["peak_gap"]=hrd["peak_gap"].apply(lambda v:fmt_ccy(v) if v>0 else "—")
    hrd.columns=["Company","AM","Facility","OB","Util %","Headroom","Peak OB","Peak Gap"]
    with st.expander(f"Headroom ({len(hr)})"):
        st.dataframe(hrd.reset_index(drop=True), use_container_width=True)

    st.markdown("##### OB Drop (30d / 90d)")
    col1, col2 = st.columns(2)
    for col, ob_col, label in [(col1,"ob30","Last 30 Days"),(col2,"ob90","Last 90 Days")]:
        with col:
            st.caption(label)
            drop = wa[wa["ob"]<wa[ob_col]].copy()
            drop["drop"] = drop["ob"]-drop[ob_col]; drop = drop.sort_values("drop")
            dd2 = drop[["company","am","ob",ob_col,"drop"]].copy()
            dd2["drop_pct"] = drop.apply(lambda r: fmt_pct(r["drop"]/r[ob_col]) if r[ob_col]>0 else "—", axis=1)
            for c in ["ob",ob_col,"drop"]: dd2[c]=dd2[c].apply(fmt_ccy)
            dd2.columns=["Company","AM","OB Now",f"OB {'30d' if ob_col=='ob30' else '90d'} Ago","Drop","Drop %"]
            st.dataframe(dd2.reset_index(drop=True), use_container_width=True, height=300)

# ══════════════════════════════════════════════════════════
# VIEW T — TEAM TRACKER
# ══════════════════════════════════════════════════════════
with tabs[6]:
    st.markdown("##### Team Tracker")
    t_am = st.selectbox("Select AM", POD_AMS, key="t_am")
    t_mode = st.radio("Mode",["Focus View","Manager Overview"], horizontal=True, key="t_mode")
    if t_mode == "Focus View":
        am_accts = fa[fa["am"]==t_am].copy()
        ov_cos_t = set(v2f[v2f["Stage"].isin({"overdue","npa"})]["buyer_lower"])
        npa_cos_t = set(v2f[v2f["Stage"]=="npa"]["buyer_lower"])
        for bname, mask in [
            ("🔴 NPA", am_accts["company"].str.lower().isin(npa_cos_t)),
            ("🟠 Overdue", am_accts["company"].str.lower().isin(ov_cos_t-npa_cos_t)),
            ("⏸ Suspended WA", am_accts["level2"]=="Suspended Workable"),
            ("🟢 Active WA",   am_accts["level2"]=="Active Workable"),
        ]:
            baccts = am_accts[mask]
            if baccts.empty: continue
            with st.expander(f"{bname} ({len(baccts)})"):
                for _, acct in baccts.iterrows():
                    kp = f"t_{t_am}_{acct['id']}"
                    c1,c2,c3,c4,c5 = st.columns([3,2,3,2,2])
                    c1.markdown(f"**{acct['company']}**"); c1.caption(f"OB {fmt_ccy(acct['ob'])} · Fac {fmt_ccy(acct['total_fac'])}")
                    c2.selectbox("Status",["—","In Progress","Contacted","Resolved","Escalated"],key=f"{kp}_s")
                    c3.text_area("Comment","",key=f"{kp}_c",height=70)
                    c4.date_input("Last Contact",value=None,key=f"{kp}_lc")
                    c5.date_input("Next Follow-up",value=None,key=f"{kp}_nf")
                    st.divider()
    else:
        ov_cos_m = set(v2f[v2f["Stage"].isin({"overdue","npa"})]["buyer_lower"])
        rows = [{"AM":am,"Total":len(fa[fa["am"]==am]),"Active WA":len(fa[(fa["am"]==am)&(fa["level2"]=="Active Workable")]),
                 "Suspended WA":len(fa[(fa["am"]==am)&(fa["level2"]=="Suspended Workable")]),
                 "Overdue/NPA":len(fa[(fa["am"]==am)&fa["company"].str.lower().isin(ov_cos_m)]),
                 "OB":fmt_ccy(fa[fa["am"]==am]["ob"].sum()),
                 "WIRR":fmt_irr(wirr(fa[(fa["am"]==am)&fa["level2"].isin(["Active Workable","Suspended Workable"])]))} for am in POD_AMS]
        st.dataframe(pd.DataFrame(rows), use_container_width=True)

# ══════════════════════════════════════════════════════════
# VIEW P — PEAK ANALYSIS
# ══════════════════════════════════════════════════════════
with tabs[7]:
    if ob_pivot.empty:
        st.info("Upload Historical OB and Current OB files to enable Peak Analysis.")
    else:
        st.markdown("##### Portfolio OB Trend")
        c1,c2 = st.columns(2)
        with c1: p_tw = st.radio("Window",["3M","6M","12M","All (Jul 2020)"], horizontal=True, key="ptw")
        with c2: p_tm = st.radio("Mode",["Portfolio Total","Per AM"], horizontal=True, key="ptm")
        tw_offsets = {"3M":pd.DateOffset(months=3),"6M":pd.DateOffset(months=6),"12M":pd.DateOffset(years=1)}
        st_tr = pd.Timestamp("2020-07-01") if p_tw=="All (Jul 2020)" else today_ts-tw_offsets[p_tw]
        pod_ids_p = set(fa["id"])
        tr_cols = [c for c in ob_pivot.columns if c in pod_ids_p]
        tr_dates = [d for d in sorted_ob_keys if pd.Timestamp(d)>=st_tr and pd.Timestamp(d)<=today_ts]
        if tr_dates:
            td = ob_pivot[tr_cols].loc[tr_dates]
            fig = go.Figure()
            if p_tm == "Portfolio Total":
                fig.add_trace(go.Scatter(x=[str(d) for d in tr_dates], y=td.sum(axis=1).values/1e6,
                    mode="lines", name="Portfolio OB", line=dict(color="#f59e0b",width=2),
                    fill="tozeroy", fillcolor="rgba(245,158,11,.1)"))
            else:
                for am, color in zip(POD_AMS, AM_COLORS):
                    am_ids = [c for c in tr_cols if c in set(fa[fa["am"]==am]["id"])]
                    if not am_ids: continue
                    fig.add_trace(go.Scatter(x=[str(d) for d in tr_dates], y=td[am_ids].sum(axis=1).values/1e6,
                        mode="lines", name=am.split()[0], line=dict(color=color,width=1.5)))
            fig.update_layout(paper_bgcolor="#0f172a",plot_bgcolor="#0f172a",font_color="#94a3b8",
                height=300,yaxis_tickprefix="$",yaxis_ticksuffix="M",
                hovermode="x unified",margin=dict(l=0,r=0,t=0,b=0))
            st.plotly_chart(fig, use_container_width=True)

        st.markdown("##### Peak vs Today")
        peak_mode = st.radio("Peak",["Auto Peak","Custom Date"], horizontal=True, key="pm")
        if peak_mode == "Custom Date":
            pk_key = closest_before(
                st.date_input("Peak Date", value=pd.Timestamp(sorted_ob_keys[-1]).date(), key="pd2"),
                sorted_ob_keys)
        else:
            pc2 = [c for c in ob_pivot.columns if c in pod_ids_p]
            pk_key = ob_pivot[pc2].sum(axis=1).idxmax() if pc2 else (sorted_ob_keys[-1] if sorted_ob_keys else None)

        if pk_key:
            pc2    = [c for c in ob_pivot.columns if c in pod_ids_p]
            ob_pk  = ob_pivot[pc2].loc[pk_key] if pk_key in ob_pivot.index else pd.Series()
            wa_ids = set(fa[fa["level2"].isin(["Active Workable","Suspended Workable"])]["id"])
            tot_pk = ob_pk.sum(); tot_now = fa["ob"].sum()
            c1,c2,c3 = st.columns(3)
            c1.metric(f"Peak OB ({pk_key})", fmt_ccy(tot_pk))
            c2.metric("Today's OB",           fmt_ccy(tot_now))
            net = tot_now-tot_pk
            c3.metric("Net Movement", fmt_ccy(net), fmt_pct(net/tot_pk if tot_pk else 0))

            chgs = [{"company":r["company"],"am":r["am"],"level2":r["level2"],
                     "ob_peak":float(ob_pk.get(r["id"],0)),"ob_today":r["ob"],"change":r["ob"]-float(ob_pk.get(r["id"],0))}
                    for _,r in fa.iterrows() if r["ob"]!=0 or float(ob_pk.get(r["id"],0))!=0]
            chgs.sort(key=lambda x: abs(x["change"]), reverse=True)
            t30 = sorted(chgs[:30], key=lambda x: x["change"])
            if t30:
                fig = go.Figure(go.Bar(x=[x["change"]/1e6 for x in t30], y=[x["company"][:25] for x in t30],
                    orientation="h", marker_color=["rgba(16,185,129,.75)" if x["change"]>=0 else "rgba(239,68,68,.75)" for x in t30]))
                fig.update_layout(paper_bgcolor="#0f172a",plot_bgcolor="#0f172a",font_color="#94a3b8",
                    height=600,xaxis_tickprefix="$",xaxis_ticksuffix="M",margin=dict(l=0,r=0,t=0,b=0))
                st.plotly_chart(fig, use_container_width=True)

# ══════════════════════════════════════════════════════════
# VIEW G — CP HEALTH
# ══════════════════════════════════════════════════════════
with tabs[8]:
    mh_full = ss.get("mh_full")
    if mh_full is None:
        st.info("CP Health uses the Master Handover file. It is loaded automatically.")
    cp_mh = load_mh.__wrapped__(ss["up_mh"]) if False else None  # use already-loaded version

    # rebuild from pod + mh data already in memory
    # CP accounts are those with Team=='CP' and Partner!='Direct'
    cp_df_rows = []
    for _, row in ss.get("mh_df_raw", pd.DataFrame()).iterrows() if "mh_df_raw" in ss else []:
        pass

    # Since we have mh processed already in pod-build logic, reconstruct CP view from raw mh
    # We re-use the already-uploaded file by seeking back to start
    try:
        ss["up_mh"].seek(0)
        mh_raw = load_mh(ss["up_mh"])
        cp_mh  = mh_raw[(mh_raw["Team"]=="CP")&(mh_raw["Partner"].str.strip()!="Direct")].copy()
        ss["up_v1"].seek(0)
        v1_raw = load_v1(ss["up_v1"])

        cp_rec = []
        for _, row in cp_mh.iterrows():
            bid = row["Buyer_ID"]
            v1r = v1_raw.loc[bid] if bid in v1_raw.index else pd.Series(dtype=object)
            fac = float(v1r.get("Facility_Size",0) or row["Facility_Size"] or 0)
            ovd = float(v1r.get("overdraft_limit",0) or row["Overdraft_Limit"] or 0)
            ob_v = v1r.get("Outstanding_Balance"); ob = float(ob_v if pd.notna(ob_v) else row["OB"] or 0)
            irr  = float(v1r.get("Signed-up IRR",0) or row["Signed_up_IRR"] or 0)
            ld   = pd.Timestamp(v1r.get("Last_Disbursed_Date") or row["Last_Disbursed_Date"]) if pd.notna(v1r.get("Last_Disbursed_Date") or row["Last_Disbursed_Date"]) else pd.NaT
            dld  = int((today_ts-ld).days) if pd.notna(ld) else None
            tfac = fac+ovd
            cp_rec.append({"id":bid,"company":str(row["Buyer"]).strip(),"am":str(row.get("AM","") or "").strip(),
                "partner":str(row.get("Partner","") or "").strip(),"total_fac":tfac,"ob":ob,"irr":irr,
                "last_disb":ld,"days_last_disb":dld,"util_pct":min(ob/tfac,1) if tfac>0 else 0})
        cp_df = pd.DataFrame(cp_rec)

        c1,c2,c3,c4 = st.columns(4)
        c1.metric("CP Accounts",  len(cp_df), "Excl. Direct")
        c2.metric("CP OB",        fmt_ccy(cp_df["ob"].sum()))
        c3.metric("CP Facility",  fmt_ccy(cp_df["total_fac"].sum()))
        tf = cp_df["total_fac"].sum()
        c4.metric("CP Util %",    fmt_pct(cp_df["ob"].sum()/tf if tf else 0))

        by_p = cp_df.groupby("partner").agg(cnt=("id","count"),ob=("ob","sum"),fac=("total_fac","sum")).sort_values("ob",ascending=False).head(20)
        fig  = go.Figure()
        fig.add_trace(go.Bar(y=by_p.index,x=by_p["fac"]/1e6,name="Facility",marker_color="rgba(148,163,184,.3)",orientation="h"))
        fig.add_trace(go.Bar(y=by_p.index,x=by_p["ob"]/1e6, name="OB",      marker_color="rgba(245,158,11,.75)",orientation="h"))
        fig.update_layout(paper_bgcolor="#0f172a",plot_bgcolor="#0f172a",font_color="#94a3b8",
            height=450,barmode="overlay",xaxis_tickprefix="$",xaxis_ticksuffix="M",margin=dict(l=0,r=0,t=0,b=0))
        st.plotly_chart(fig, use_container_width=True)

        ss["up_v2"].seek(0)
        v2_raw2 = load_v2(ss["up_v2"])
        cp_cos  = set(cp_mh["Buyer"].astype(str).str.lower())
        v2_cp   = v2_raw2[v2_raw2["buyer_lower"].isin(cp_cos)].copy()
        v2_cp["dpd2"] = pd.to_numeric(v2_cp["dpd"],errors="coerce").fillna(0)
        ov_cos_g = set(v2_cp[v2_cp["Stage"].isin(OPEN_ST)&(v2_cp["dpd2"]>7)]["buyer_lower"])
        act90    = set(v2_cp[v2_cp["disbursed_date"].notna()&(v2_cp["disbursed_date"]>=(today_ts-timedelta(days=90)))]["buyer_lower"])
        cp_df["score"] = (
            (cp_df["util_pct"]*25).clip(0,25) +
            cp_df["company"].str.lower().apply(lambda c: 0 if c in ov_cos_g else 25) +
            cp_df["days_last_disb"].apply(lambda d: 25 if d is not None and d<=30 else 0) +
            cp_df["company"].str.lower().apply(lambda c: 25 if c in act90 else 0)
        ).round().astype(int)

        st.markdown("##### Partner Health Scorecard")
        for partner, grp in cp_df.groupby("partner"):
            avg = grp["score"].mean(); em = "🟢" if avg>=75 else ("🟡" if avg>=50 else "🔴")
            ob_p = grp["ob"].sum(); fac_p = grp["total_fac"].sum()
            with st.expander(f"{em} {partner} — {len(grp)} accts · Score {avg:.0f}/100 · OB {fmt_ccy(ob_p)} · {fmt_pct(ob_p/fac_p if fac_p else 0)} util"):
                gd = grp.sort_values("score",ascending=False)[["company","am","total_fac","ob","util_pct","irr","score"]].copy()
                for c in ["total_fac","ob"]: gd[c]=gd[c].apply(fmt_ccy)
                gd["util_pct"]=gd["util_pct"].apply(fmt_pct); gd["irr"]=gd["irr"].apply(fmt_irr); gd["score"]=gd["score"].astype(str)+"/100"
                gd.columns=["Account","AM","Facility","OB","Util %","IRR","Health Score"]
                st.dataframe(gd.reset_index(drop=True), use_container_width=True)
    except Exception as e:
        st.error(f"CP Health error: {e}")
