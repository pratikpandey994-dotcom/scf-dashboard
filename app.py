from __future__ import annotations

from datetime import date

import pandas as pd
import plotly.express as px
import streamlit as st

from data_loader import DEFAULT_FILES, load_data
from metrics import (
    TEAMS,
    am_summary,
    apply_filters,
    build_portfolio,
    filter_team,
    ob_trend,
    portfolio_kpis,
    utilization_buckets,
)


st.set_page_config(
    page_title="Portfolio Dashboard",
    page_icon="SCF",
    layout="wide",
    initial_sidebar_state="expanded",
)


def fmt_money(value: float | int | None) -> str:
    if value is None or pd.isna(value):
        return "-"
    value = float(value)
    if abs(value) >= 1_000_000:
        return f"${value / 1_000_000:.2f}M"
    if abs(value) >= 1_000:
        return f"${value / 1_000:.1f}K"
    return f"${value:,.0f}"


def fmt_pct(value: float | int | None) -> str:
    if value is None or pd.isna(value):
        return "-"
    return f"{float(value) * 100:.1f}%"


def metric_row(kpis: dict[str, float | int | None]) -> None:
    cols = st.columns(5)
    cols[0].metric("Accounts", f"{int(kpis['accounts']):,}")
    cols[1].metric("Total Facility", fmt_money(kpis["total_facility"]))
    cols[2].metric("Total OB", fmt_money(kpis["total_ob"]))
    cols[3].metric("Utilization", fmt_pct(kpis["utilization"]))
    cols[4].metric("MTD Repayments", fmt_money(kpis["mtd_repayments"]))

    cols = st.columns(5)
    cols[0].metric("Net OB", fmt_money(kpis["net_ob"]))
    cols[1].metric("Gap to 75%", fmt_money(kpis["gap_to_75"]))
    cols[2].metric("Zero OB", f"{int(kpis['zero_ob']):,}")
    cols[3].metric("Overdue OB", fmt_money(kpis["overdue_ob"]))
    cols[4].metric("WIRR", "-" if kpis["wirr"] is None else f"{float(kpis['wirr']):.2f}%")


def data_config() -> dict:
    return {
        "facility": st.column_config.NumberColumn("Facility", format="$ %.0f"),
        "overdraft": st.column_config.NumberColumn("Overdraft", format="$ %.0f"),
        "total_facility": st.column_config.NumberColumn("Total Facility", format="$ %.0f"),
        "ob": st.column_config.NumberColumn("OB", format="$ %.0f"),
        "mtd_repayments": st.column_config.NumberColumn("MTD Repayments", format="$ %.0f"),
        "net_ob": st.column_config.NumberColumn("Net OB", format="$ %.0f"),
        "target_ob_75": st.column_config.NumberColumn("Target OB 75%", format="$ %.0f"),
        "gap_to_75": st.column_config.NumberColumn("Gap to 75%", format="$ %.0f"),
        "utilization_pct": st.column_config.NumberColumn("Utilization", format="%.1f%%"),
        "ob_dent_30d": st.column_config.NumberColumn("30d OB Dent", format="$ %.0f"),
        "ob_dent_30d_pct_display": st.column_config.NumberColumn("30d Dent %", format="%.1f%%"),
        "last_disbursed": st.column_config.DateColumn("Last Disbursed"),
    }


def show_source_defaults() -> None:
    with st.expander("Default file paths", expanded=False):
        for label, path in DEFAULT_FILES.items():
            st.caption(f"{label}: {path}")


def show_zero_ob(accounts: pd.DataFrame) -> None:
    zero_rows = accounts[accounts["ob"] < 1].copy()
    high_facility = zero_rows[zero_rows["total_facility"] >= 500_000]
    recently_active = zero_rows[(zero_rows["ob_30d"] > 0) | (zero_rows["days_since_last"].fillna(9999) <= 90)]
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Zero OB accounts", f"{len(zero_rows):,}")
    c2.metric("High facility zero OB", f"{len(high_facility):,}")
    c3.metric("Recently active", f"{len(recently_active):,}")
    c4.metric("Dormant facility", fmt_money(zero_rows["total_facility"].sum()))
    st.dataframe(
        zero_rows[
            ["company", "am", "raw_status", "total_facility", "ob", "ob_30d", "last_disbursed", "days_since_last"]
        ].sort_values("total_facility", ascending=False),
        use_container_width=True,
        hide_index=True,
        column_config=data_config(),
    )


def show_workable_inactive(accounts: pd.DataFrame) -> None:
    inactive = accounts[
        accounts["raw_status"].astype(str).str.contains("Inactive|Temporarily suspended|Suspended", case=False, na=False)
        & (accounts["days_since_last"].fillna(9999) <= 365)
    ].copy()
    inactive["months_since_last"] = inactive["days_since_last"].fillna(0) / 30
    c1, c2, c3 = st.columns(3)
    c1.metric("Workable inactive <=12 mo", f"{len(inactive):,}")
    c2.metric("Facility available", fmt_money(inactive["total_facility"].sum()))
    c3.metric("Gap to 75%", fmt_money(inactive["gap_to_75"].sum()))
    st.dataframe(
        inactive[
            ["company", "am", "raw_status", "total_facility", "ob", "gap_to_75", "last_disbursed", "months_since_last"]
        ].sort_values("total_facility", ascending=False),
        use_container_width=True,
        hide_index=True,
        column_config=data_config(),
    )


def show_ob_dent(accounts: pd.DataFrame, ob_pivot: pd.DataFrame) -> None:
    valid = accounts[(accounts["ob"] > 0) | (accounts["ob_30d"] > 0)].copy()
    reduced_30 = valid[valid["ob_dent_30d"] > 0]
    reduced_90 = valid[valid["ob_dent_90d"] > 0]
    flagged = valid[(valid["ob_dent_30d_pct"] > 0.25) | (valid["ob_dent_30d"] > 100_000)]
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("OB reduced in 30d", f"{len(reduced_30):,}")
    c2.metric("OB reduced in 90d", f"{len(reduced_90):,}")
    c3.metric("30d OB reduction", fmt_money(reduced_30["ob_dent_30d"].sum()))
    c4.metric("Recovery candidates", f"{len(flagged):,}")
    trend = ob_trend(ob_pivot, set(accounts["id"]))
    if not trend.empty:
        fig = px.line(trend.tail(180), x="date", y="ob", title="Portfolio OB Movement - 180 Day Window")
        st.plotly_chart(fig, use_container_width=True)
    st.dataframe(
        valid[
            [
                "company",
                "am",
                "raw_status",
                "ob_30d",
                "ob",
                "ob_dent_30d",
                "ob_dent_30d_pct_display",
                "ob_90d",
                "ob_dent_90d",
            ]
        ].sort_values("ob_dent_30d", ascending=False),
        use_container_width=True,
        hide_index=True,
        column_config=data_config(),
    )


def show_am_performance(accounts: pd.DataFrame, invoices: pd.DataFrame, cfg) -> None:
    rows = []
    for am in cfg.ams:
        accts = accounts[accounts["am"] == am]
        inv = invoices[invoices["am"] == am] if not invoices.empty else invoices
        originations = inv["Origination"].sum() if not inv.empty and "Origination" in inv else 0
        repayments = accts["mtd_repayments"].sum() if "mtd_repayments" in accts else 0
        kpi = portfolio_kpis(accts, inv) if not accts.empty else {"wirr": None}
        rows.append(
            {
                "am": am,
                "accounts": len(accts),
                "facility": accts["total_facility"].sum(),
                "ob": accts["ob"].sum(),
                "avg_utilization": accts["utilization_pct"].mean() if len(accts) else 0,
                "zero_ob": int((accts["ob"] < 1).sum()) if len(accts) else 0,
                "inactive": int(accts["raw_status"].astype(str).str.contains("Inactive", case=False, na=False).sum())
                if len(accts)
                else 0,
                "repayments": repayments,
                "originations": originations,
                "wirr": "-" if kpi["wirr"] is None else f"{kpi['wirr']:.2f}%",
            }
        )
    perf = pd.DataFrame(rows)
    if perf.empty:
        st.info("No AM data available for this division.")
        return
    fig = px.bar(perf, x="am", y=["ob", "repayments", "originations"], barmode="group", title="AM Performance")
    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(perf, use_container_width=True, hide_index=True, column_config=data_config())


def show_75_engine(accounts: pd.DataFrame) -> None:
    opps = accounts[
        (accounts["gap_to_75"] > 0)
        & (accounts["total_facility"] > 0)
        & accounts["raw_status"].astype(str).str.contains("Workable|Active|Suspended|Inactive", case=False, na=False)
    ].copy()
    c1, c2, c3 = st.columns(3)
    c1.metric("Opportunity accounts", f"{len(opps):,}")
    c2.metric("Total gap to 75%", fmt_money(opps["gap_to_75"].sum()))
    c3.metric("Average current utilization", fmt_pct(opps["utilization"].mean() if len(opps) else 0))
    st.caption("Formula: gap to 75% = total facility * 75% - current OB.")
    st.dataframe(
        opps[
            ["company", "am", "raw_status", "total_facility", "ob", "target_ob_75", "utilization_pct", "gap_to_75", "last_disbursed"]
        ].sort_values("gap_to_75", ascending=False),
        use_container_width=True,
        hide_index=True,
        column_config=data_config(),
    )


def show_opportunity_views(accounts: pd.DataFrame, cfg) -> None:
    top_gap = accounts[(accounts["gap_to_75"] > 0) & (accounts["raw_status"].astype(str).str.contains("Workable|Active|Suspended|Inactive", case=False, na=False))]
    dormant = accounts[accounts["days_since_last"].fillna(0) >= 90]
    high_facility_low_util = accounts[(accounts["total_facility"] >= 500_000) & (accounts["utilization"] < 0.30)]
    st.subheader("Top 20 Utilization Opportunities")
    st.dataframe(
        top_gap[["company", "am", "total_facility", "ob", "utilization_pct", "gap_to_75"]]
        .sort_values("gap_to_75", ascending=False)
        .head(20),
        use_container_width=True,
        hide_index=True,
        column_config=data_config(),
    )
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Not Funded 90+ Days")
        st.dataframe(
            dormant[["company", "am", "total_facility", "ob", "days_since_last", "raw_status"]].sort_values(
                "days_since_last", ascending=False
            ),
            use_container_width=True,
            hide_index=True,
            column_config=data_config(),
        )
    with col2:
        st.subheader("High Facility / Low Utilization")
        st.dataframe(
            high_facility_low_util[["company", "am", "total_facility", "ob", "utilization_pct", "gap_to_75"]].sort_values(
                "total_facility", ascending=False
            ),
            use_container_width=True,
            hide_index=True,
            column_config=data_config(),
        )
    ranking = []
    for am in cfg.ams:
        am_opps = top_gap[top_gap["am"] == am]
        all_am = accounts[(accounts["am"] == am) & (accounts["total_facility"] > 0)]
        ranking.append(
            {
                "am": am,
                "opportunity_accounts": len(am_opps),
                "total_gap": am_opps["gap_to_75"].sum(),
                "avg_utilization": all_am["utilization_pct"].mean() if len(all_am) else 0,
            }
        )
    st.subheader("AM Opportunity Ranking")
    st.dataframe(pd.DataFrame(ranking).sort_values("total_gap", ascending=False), use_container_width=True, hide_index=True)


def show_action_pulse(accounts: pd.DataFrame, invoices: pd.DataFrame) -> None:
    declining = accounts[(accounts["ob_dent_30d"] > 0) | (accounts["ob_dent_90d"] > 0)].copy()
    headroom = accounts[(accounts["days_since_last"].fillna(0) < 120) & (accounts["total_facility"] > accounts["ob"])].copy()
    headroom["headroom"] = (headroom["total_facility"] - headroom["ob"]).clip(lower=0)
    reactivation = accounts[
        accounts["raw_status"].astype(str).str.contains("Suspended|Inactive", case=False, na=False)
        | (accounts["days_since_last"].fillna(0) >= 180)
    ].copy()
    early_repayments = pd.DataFrame()
    if not invoices.empty and {"settlement_date", "due_date_of_invoice", "Origination", "Buyer", "am"}.issubset(invoices.columns):
        early_repayments = invoices[
            invoices["settlement_date"].notna()
            & invoices["due_date_of_invoice"].notna()
            & (invoices["settlement_date"] < invoices["due_date_of_invoice"])
        ].copy()
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Declining Accounts")
        st.dataframe(
            declining[["company", "am", "ob_30d", "ob", "ob_dent_30d", "ob_dent_30d_pct_display", "raw_status"]].sort_values(
                "ob_dent_30d", ascending=False
            ),
            use_container_width=True,
            hide_index=True,
            column_config=data_config(),
        )
        st.subheader("Reactivation Focus")
        st.dataframe(
            reactivation[["company", "am", "raw_status", "total_facility", "ob", "peak_ob", "days_since_last"]].sort_values(
                "peak_ob", ascending=False
            ),
            use_container_width=True,
            hide_index=True,
            column_config=data_config(),
        )
    with col2:
        st.subheader("Headroom Opportunity")
        st.dataframe(
            headroom[["company", "am", "total_facility", "ob", "utilization_pct", "headroom", "peak_ob"]].sort_values(
                "headroom", ascending=False
            ),
            use_container_width=True,
            hide_index=True,
            column_config=data_config(),
        )
        st.subheader("Early Repayment Tracking")
        if early_repayments.empty:
            st.info("No early repayments found in the selected view.")
        else:
            st.dataframe(
                early_repayments[["Buyer", "am", "Origination", "Outstanding", "settlement_date", "due_date_of_invoice"]].sort_values(
                    "Origination", ascending=False
                ),
                use_container_width=True,
                hide_index=True,
            )


def show_cp_health(accounts: pd.DataFrame, invoices: pd.DataFrame, today_value) -> None:
    if accounts.empty:
        st.info("No CP accounts available.")
        return
    open_invoices = invoices[invoices["Stage"].isin({"advanced", "overdue", "npa", "partial"})] if not invoices.empty else invoices
    overdue_ids = set(open_invoices.loc[open_invoices["dpd"] > 7, "account_id"]) if not open_invoices.empty else set()
    active_90_ids = set(
        invoices.loc[
            invoices["disbursed_date"].notna()
            & (invoices["disbursed_date"] >= pd.Timestamp(today_value) - pd.Timedelta(days=90)),
            "account_id",
        ]
    ) if not invoices.empty and "disbursed_date" in invoices else set()
    cp = accounts.copy()
    cp["health_score"] = (
        (cp["utilization"].clip(0, 1) * 25)
        + cp["id"].apply(lambda account_id: 0 if account_id in overdue_ids else 25)
        + cp["days_since_last"].apply(lambda days: 25 if pd.notna(days) and days <= 30 else 0)
        + cp["id"].apply(lambda account_id: 25 if account_id in active_90_ids else 0)
    ).round()
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("CP accounts", f"{len(cp):,}")
    c2.metric("CP OB", fmt_money(cp["ob"].sum()))
    c3.metric("CP facility", fmt_money(cp["total_facility"].sum()))
    c4.metric("CP utilization", fmt_pct(cp["ob"].sum() / cp["total_facility"].sum() if cp["total_facility"].sum() else 0))
    by_partner = cp.groupby("partner", as_index=False).agg(accounts=("id", "count"), ob=("ob", "sum"), facility=("total_facility", "sum"))
    if not by_partner.empty:
        fig = px.bar(by_partner.sort_values("ob", ascending=False).head(20), y="partner", x=["facility", "ob"], orientation="h", title="OB and Facility by Partner")
        st.plotly_chart(fig, use_container_width=True)
    st.dataframe(
        cp[["partner", "company", "am", "total_facility", "ob", "utilization_pct", "irr", "health_score"]].sort_values(
            ["partner", "health_score"], ascending=[True, False]
        ),
        use_container_width=True,
        hide_index=True,
        column_config=data_config(),
    )


def show_tracker(accounts: pd.DataFrame, invoices: pd.DataFrame, cfg, team_name: str) -> None:
    tracker_options = [am for am in cfg.ams if am in set(accounts["am"])]
    if not tracker_options:
        st.info("No account managers available for tracker view.")
        return
    selected_tracker_am = st.selectbox("Tracker Account Manager", tracker_options, key=f"{team_name}_tracker_am")
    mode = st.radio("Tracker view", ["Focus View", "Manager Overview"], horizontal=True, key=f"{team_name}_tracker_mode")
    open_ids = set(invoices.loc[invoices["Stage"].isin({"overdue", "npa"}), "account_id"]) if not invoices.empty else set()
    npa_ids = set(invoices.loc[invoices["Stage"].eq("npa"), "account_id"]) if not invoices.empty else set()
    if mode == "Manager Overview":
        rows = []
        for am in cfg.ams:
            accts = accounts[accounts["am"] == am]
            rows.append(
                {
                    "AM": am,
                    "Total": len(accts),
                    "Active": int(accts["raw_status"].astype(str).str.contains("Active", case=False, na=False).sum()) if len(accts) else 0,
                    "Suspended": int(accts["raw_status"].astype(str).str.contains("Suspended", case=False, na=False).sum()) if len(accts) else 0,
                    "Overdue/NPA": int(accts["id"].isin(open_ids).sum()) if len(accts) else 0,
                    "OB": fmt_money(accts["ob"].sum()),
                }
            )
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        return
    focus = accounts[accounts["am"] == selected_tracker_am]
    buckets = {
        "NPA": focus[focus["id"].isin(npa_ids)],
        "Overdue": focus[focus["id"].isin(open_ids - npa_ids)],
        "Suspended": focus[focus["raw_status"].astype(str).str.contains("Suspended", case=False, na=False)],
        "Active": focus[focus["raw_status"].astype(str).str.contains("Active", case=False, na=False)],
    }
    for label, frame in buckets.items():
        with st.expander(f"{label} - {len(frame)} accounts"):
            if frame.empty:
                st.caption("No accounts in this bucket.")
                continue
            st.dataframe(
                frame[["company", "am", "raw_status", "total_facility", "ob", "utilization_pct", "last_disbursed"]],
                use_container_width=True,
                hide_index=True,
                column_config=data_config(),
            )


def show_peak(accounts: pd.DataFrame, ob_pivot: pd.DataFrame) -> None:
    trend = ob_trend(ob_pivot, set(accounts["id"]))
    if trend.empty:
        st.info("Upload historical/current OB files to enable peak and contribution analysis.")
        return
    fig = px.line(trend, x="date", y="ob", title="Portfolio OB Trend")
    st.plotly_chart(fig, use_container_width=True)
    peak_row = trend.loc[trend["ob"].idxmax()]
    current_ob = accounts["ob"].sum()
    c1, c2, c3 = st.columns(3)
    c1.metric(f"Peak OB ({peak_row['date'].date()})", fmt_money(peak_row["ob"]))
    c2.metric("Today's OB", fmt_money(current_ob))
    c3.metric("Net movement", fmt_money(current_ob - peak_row["ob"]))
    peak_date = peak_row["date"].date()
    if peak_date in ob_pivot.index:
        peak_values = ob_pivot.loc[peak_date]
        change = accounts.copy()
        change["ob_peak"] = change["id"].map(peak_values).fillna(0)
        change["change"] = change["ob"] - change["ob_peak"]
        fig = px.bar(
            change.reindex(change["change"].abs().sort_values(ascending=False).index).head(30).sort_values("change"),
            x="change",
            y="company",
            orientation="h",
            title="Top Account Contribution to Change",
        )
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(
            change[["company", "am", "raw_status", "ob_peak", "ob", "change"]].sort_values("change"),
            use_container_width=True,
            hide_index=True,
            column_config=data_config(),
        )


st.title("Portfolio Dashboard")
st.caption("Select Team Nikhil or Team Pankit to view the matching AM list, account mix, and portfolio visuals.")

with st.sidebar:
    st.header("Data")
    use_uploads = st.toggle("Upload files manually", value=False)
    uploads = {}
    if use_uploads:
        uploads["master_file"] = st.file_uploader("Master data", type=["xlsx", "xls"], key="master_file")
        uploads["view1_file"] = st.file_uploader("View 1", type=["xlsx", "xls"], key="view1_file")
        uploads["view2_file"] = st.file_uploader("View 2", type=["xlsx", "xls"], key="view2_file")
        uploads["historic_ob_file"] = st.file_uploader("Historic OB", type=["xlsx", "xls"], key="historic_ob_file")
        uploads["current_ob_file"] = st.file_uploader("Current OB", type=["xlsx", "xls"], key="current_ob_file")
    else:
        show_source_defaults()

    st.header("View")
    today_value = st.date_input("As of date", value=date(2026, 6, 5), key="as_of_date")

try:
    raw = load_data(**uploads) if use_uploads else load_data()
    accounts_all, invoices_all, ob_pivot = build_portfolio(
        raw["master"],
        raw["view1"],
        raw["view2"],
        raw["ob_history"],
        pd.Timestamp(today_value),
    )
except Exception as exc:
    st.error(str(exc))
    st.stop()

team_name = st.radio(
    "Division",
    list(TEAMS.keys()),
    horizontal=True,
    key="team_name",
)

team_accounts = filter_team(accounts_all, team_name)
team_invoices = invoices_all[invoices_all["account_id"].isin(set(team_accounts["id"]))]
cfg = TEAMS[team_name]

if team_accounts.empty:
    st.warning("No accounts matched this team segment and AM list.")
    st.stop()

am_counts = team_accounts["am"].value_counts().to_dict()
am_options = ["All"] + [am for am in cfg.ams if am in am_counts]
selected_am = st.selectbox(
    "Account Manager",
    am_options,
    format_func=lambda value: "All Account Managers" if value == "All" else f"{value} ({am_counts.get(value, 0)})",
    key=f"{team_name}_am",
)

filter_cols = st.columns(2)
with filter_cols[0]:
    account_type_options = sorted(team_accounts["account_type"].dropna().unique().tolist())
    selected_account_types = st.multiselect(
        "Account type",
        account_type_options,
        default=[],
        key=f"{team_name}_account_types",
        help="Leave blank for all account types.",
    )
with filter_cols[1]:
    status_options = sorted(team_accounts["raw_status"].dropna().astype(str).unique().tolist())
    selected_statuses = st.multiselect(
        "Raw status",
        status_options,
        default=[],
        key=f"{team_name}_raw_statuses",
        help="Leave blank for all raw statuses in this division.",
    )

accounts = apply_filters(team_accounts, selected_am, selected_account_types, selected_statuses)
invoices = team_invoices[team_invoices["account_id"].isin(set(accounts["id"]))]
kpis = portfolio_kpis(accounts, invoices)

st.subheader(f"{team_name} - {'All Account Managers' if selected_am == 'All' else selected_am}")
st.caption(
    "Utilization and 75% targets use total facility = facility size + overdraft. "
    "Each division keeps its own AM list, account type filters, and raw status filters."
)
metric_row(kpis)

tab_labels = ["Snapshot", "Accounts", "Utilization", "Repayments", "Opportunities", "OB Trend"]
if team_name == "Team Nikhil":
    tab_labels.extend(["AM Performance", "Action Pulse", "CP Health", "Tracker", "Peak"])
elif team_name == "Team Pankit":
    tab_labels.extend(["Zero OB", "Workable Inactive", "OB Dent", "AM Performance", "75% Engine", "Opportunity Views"])
tabs = st.tabs(tab_labels)

with tabs[0]:
    left, right = st.columns([1.2, 1])
    with left:
        summary = am_summary(accounts if selected_am != "All" else team_accounts)
        if not summary.empty:
            fig = px.bar(
                summary,
                x="am",
                y=["ob", "facility"],
                barmode="group",
                labels={"value": "USD", "am": "AM", "variable": "Metric"},
                title="AM Portfolio Scale",
            )
            st.plotly_chart(fig, use_container_width=True)
            st.dataframe(summary, use_container_width=True, hide_index=True, column_config=data_config())
    with right:
        type_summary = (
            accounts.groupby("account_type", as_index=False)
            .agg(accounts=("id", "count"), ob=("ob", "sum"), facility=("total_facility", "sum"))
            .sort_values("ob", ascending=False)
        )
        if not type_summary.empty:
            fig = px.pie(type_summary, values="ob", names="account_type", hole=0.55, title="OB by Account Type")
            st.plotly_chart(fig, use_container_width=True)
            st.dataframe(type_summary, use_container_width=True, hide_index=True, column_config=data_config())

with tabs[1]:
    st.dataframe(
        accounts[
            [
                "company",
                "am",
                "partner",
                "account_type",
                "raw_status",
                "total_facility",
                "ob",
                "mtd_repayments",
                "net_ob",
                "utilization_pct",
                "target_ob_75",
                "gap_to_75",
                "last_disbursed",
                "days_since_last",
            ]
        ].sort_values("total_facility", ascending=False),
        use_container_width=True,
        hide_index=True,
        column_config=data_config(),
    )

with tabs[2]:
    bucket_df = utilization_buckets(accounts)
    col1, col2 = st.columns([1, 1])
    with col1:
        fig = px.bar(bucket_df, x="Bucket", y="Accounts", text="Accounts", title="Utilization Buckets")
        st.plotly_chart(fig, use_container_width=True)
    with col2:
        high = int((accounts["utilization"] >= 0.75).sum())
        low = int(((accounts["utilization"] > 0) & (accounts["utilization"] < 0.50)).sum())
        st.metric("At or above 75%", f"{high:,}")
        st.metric("Below 50% but funded", f"{low:,}")
        st.metric("Average utilization", fmt_pct(accounts["utilization"].mean() if len(accounts) else 0))
    st.dataframe(
        accounts.sort_values("utilization", ascending=False)[
            ["company", "am", "account_type", "total_facility", "ob", "utilization_pct", "gap_to_75"]
        ],
        use_container_width=True,
        hide_index=True,
        column_config=data_config(),
    )

with tabs[3]:
    with_repay = accounts[accounts["mtd_repayments"] > 0].sort_values("mtd_repayments", ascending=False)
    cols = st.columns(3)
    cols[0].metric("Accounts with MTD repayments", f"{len(with_repay):,}")
    cols[1].metric("Total MTD repayments", fmt_money(with_repay["mtd_repayments"].sum()))
    cols[2].metric("Net OB after repayments", fmt_money(accounts["net_ob"].sum()))
    st.dataframe(
        with_repay[
            ["company", "am", "account_type", "ob_30d", "ob", "mtd_repayments", "net_ob", "utilization_pct"]
        ],
        use_container_width=True,
        hide_index=True,
        column_config=data_config(),
    )

with tabs[4]:
    opps = accounts[(accounts["gap_to_75"] > 0) & (accounts["total_facility"] > 0)].copy()
    dormant = accounts[(accounts["days_since_last"].fillna(9999) >= 90)].copy()
    zero_ob = accounts[accounts["ob"] < 1].copy()
    c1, c2, c3 = st.columns(3)
    c1.metric("Opportunity accounts", f"{len(opps):,}", fmt_money(opps["gap_to_75"].sum()))
    c2.metric("Not funded 90+ days", f"{len(dormant):,}")
    c3.metric("Zero OB accounts", f"{len(zero_ob):,}", fmt_money(zero_ob["total_facility"].sum()))

    view = st.radio(
        "Opportunity view",
        ["Gap to 75%", "Not Funded 90+ Days", "Zero OB", "30d OB Dent"],
        horizontal=True,
        key=f"{team_name}_opp_view",
    )
    if view == "Gap to 75%":
        frame = opps.sort_values("gap_to_75", ascending=False)
    elif view == "Not Funded 90+ Days":
        frame = dormant.sort_values("days_since_last", ascending=False)
    elif view == "Zero OB":
        frame = zero_ob.sort_values("total_facility", ascending=False)
    else:
        frame = accounts[(accounts["ob_dent_30d_pct"] > 0.25) | (accounts["ob_dent_30d"] > 100_000)].sort_values(
            "ob_dent_30d", ascending=False
        )

    st.dataframe(
        frame[
            [
                "company",
                "am",
                "account_type",
                "total_facility",
                "ob",
                "utilization_pct",
                "gap_to_75",
                "last_disbursed",
                "days_since_last",
                "ob_dent_30d",
                "ob_dent_30d_pct_display",
            ]
        ],
        use_container_width=True,
        hide_index=True,
        column_config=data_config(),
    )

with tabs[5]:
    trend = ob_trend(ob_pivot, set(accounts["id"]))
    if trend.empty:
        st.info("Upload historical/current OB files to enable the OB trend.")
    else:
        fig = px.line(trend, x="date", y="ob", title="Portfolio OB Trend", labels={"ob": "OB", "date": "Date"})
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(trend.tail(60), use_container_width=True, hide_index=True)

if team_name == "Team Nikhil":
    with tabs[6]:
        show_am_performance(accounts, invoices, cfg)
    with tabs[7]:
        show_action_pulse(accounts, invoices)
    with tabs[8]:
        show_cp_health(accounts, invoices, today_value)
    with tabs[9]:
        show_tracker(accounts, invoices, cfg, team_name)
    with tabs[10]:
        show_peak(accounts, ob_pivot)
elif team_name == "Team Pankit":
    with tabs[6]:
        show_zero_ob(accounts)
    with tabs[7]:
        show_workable_inactive(accounts)
    with tabs[8]:
        show_ob_dent(accounts, ob_pivot)
    with tabs[9]:
        show_am_performance(accounts, invoices, cfg)
    with tabs[10]:
        show_75_engine(accounts)
    with tabs[11]:
        show_opportunity_views(accounts, cfg)
