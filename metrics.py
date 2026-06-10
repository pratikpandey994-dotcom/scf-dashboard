from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

import numpy as np
import pandas as pd


NIKHIL_AMS = ["Nikhil Shetty", "Darshan Hublikar", "Deepsayan Dam", "Ashitha Nair", "Asif Ali"]
PANKIT_AMS = ["Pankit Shah", "Sonal Mishra", "Pejush Hal", "Kaustav Das"]

SETTLED = {"closed", "paid", "received"}
REPAYMENT_STAGES = SETTLED | {"partial"}
OPEN_STAGES = {"advanced", "overdue", "npa", "partial"}


@dataclass(frozen=True)
class TeamConfig:
    label: str
    leader: str
    ams: list[str]
    segment: str


TEAMS = {
    "Team Nikhil": TeamConfig(
        label="Team Nikhil",
        leader="Nikhil Shetty",
        ams=NIKHIL_AMS,
        segment="cp_partner",
    ),
    "Team Pankit": TeamConfig(
        label="Team Pankit",
        leader="Pankit Shah",
        ams=PANKIT_AMS,
        segment="direct",
    ),
}


def _first_valid(*values):
    for value in values:
        if pd.notna(value) and str(value).strip() not in {"", "nan", "None"}:
            return value
    return None


def _classify_level(broad_status: str, utilization_status: str, days_since: float | None) -> str:
    if str(broad_status).strip() != "Workable":
        return "NWA"
    if days_since is None or pd.isna(days_since) or days_since > 365:
        return "Workable >365"
    if str(utilization_status).strip().casefold() == "active":
        return "Active Workable"
    return "Suspended Workable"


def _partner_segment(partner: str) -> str:
    normalized = str(partner or "").strip().casefold()
    return "direct" if normalized in {"", "direct", "nan", "none"} else "cp_partner"


def _closest_ob(ob_pivot: pd.DataFrame, account_id: str, target_date: pd.Timestamp) -> float:
    if ob_pivot.empty or account_id not in ob_pivot.columns:
        return 0.0
    candidates = [idx for idx in ob_pivot.index if pd.Timestamp(idx) <= target_date]
    if not candidates:
        return 0.0
    return float(ob_pivot.loc[max(candidates), account_id])


def build_portfolio(
    master: pd.DataFrame,
    view1: pd.DataFrame,
    view2: pd.DataFrame,
    ob_history: pd.DataFrame,
    today: pd.Timestamp,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    rows: list[dict] = []
    today = pd.Timestamp(today)

    for _, row in master.iterrows():
        account_id = row["Buyer_ID"]
        v1_row = view1.loc[account_id] if account_id in view1.index else pd.Series(dtype=object)
        am = str(_first_valid(v1_row.get("AM_Name"), row.get("AM"), "Unassigned")).strip()
        last_disb = _first_valid(v1_row.get("Last_Disbursed_Date"), row.get("Last_Disbursed_Date"))
        first_disb = _first_valid(v1_row.get("First_Disbursed_Date"), row.get("First_Disbursed_Date"))
        last_disb = pd.Timestamp(last_disb) if pd.notna(last_disb) else pd.NaT
        first_disb = pd.Timestamp(first_disb) if pd.notna(first_disb) else pd.NaT
        days_since = int((today - last_disb).days) if pd.notna(last_disb) else None

        facility = float(_first_valid(v1_row.get("Facility_Size"), row.get("Facility_Size"), 0) or 0)
        overdraft = float(_first_valid(v1_row.get("overdraft_limit"), row.get("Overdraft_Limit"), 0) or 0)
        total_facility = facility + overdraft
        ob = float(_first_valid(v1_row.get("Outstanding_Balance"), row.get("OB"), 0) or 0)
        irr = float(_first_valid(v1_row.get("Signed-up IRR"), row.get("Signed_up_IRR"), 0) or 0)
        utilization = ob / total_facility if total_facility > 0 else 0

        partner = str(row.get("Partner", "") or "").strip()
        level = _classify_level(row.get("Broad_Account_Status", ""), v1_row.get("utilization_status", ""), days_since)
        rows.append(
            {
                "id": account_id,
                "company": row["Buyer"],
                "buyer_lower": str(row["Buyer"]).casefold(),
                "am": am,
                "partner": partner,
                "partner_segment": _partner_segment(partner),
                "team": row.get("Team", ""),
                "raw_status": row.get("Account_Status", ""),
                "broad_status": row.get("Broad_Account_Status", ""),
                "account_type": level,
                "facility": facility,
                "overdraft": overdraft,
                "total_facility": total_facility,
                "ob": ob,
                "irr": irr,
                "utilization": utilization,
                "target_ob_75": total_facility * 0.75,
                "gap_to_75": max(total_facility * 0.75 - ob, 0),
                "first_disbursed": first_disb,
                "last_disbursed": last_disb,
                "days_since_last": days_since,
            }
        )

    accounts = pd.DataFrame(rows)
    if accounts.empty:
        return accounts, view2.iloc[0:0].copy(), pd.DataFrame()

    account_ids = set(accounts["id"])
    ob_pivot = pd.DataFrame()
    if not ob_history.empty:
        ob_subset = ob_history[ob_history["importer_user_id"].isin(account_ids)].copy()
        if not ob_subset.empty:
            ob_subset["date_key"] = ob_subset["ob_date"].dt.date
            ob_pivot = ob_subset.groupby(["date_key", "importer_user_id"])["ob"].last().unstack(fill_value=0)
            accounts["peak_ob"] = accounts["id"].map(ob_pivot.max(axis=0)).fillna(0)
            accounts["avg_ob"] = accounts["id"].map(ob_pivot.replace(0, np.nan).mean(axis=0)).fillna(0)
            accounts["ob_30d"] = accounts["id"].apply(lambda account_id: _closest_ob(ob_pivot, account_id, today - timedelta(days=30)))
            accounts["ob_90d"] = accounts["id"].apply(lambda account_id: _closest_ob(ob_pivot, account_id, today - timedelta(days=90)))
        else:
            accounts[["peak_ob", "avg_ob", "ob_30d", "ob_90d"]] = 0
    else:
        accounts[["peak_ob", "avg_ob", "ob_30d", "ob_90d"]] = 0

    accounts["ob_dent_30d"] = accounts["ob_30d"] - accounts["ob"]
    accounts["ob_dent_90d"] = accounts["ob_90d"] - accounts["ob"]
    accounts["ob_dent_30d_pct"] = np.where(accounts["ob_30d"] > 0, accounts["ob_dent_30d"] / accounts["ob_30d"], 0)
    accounts["utilization_pct"] = accounts["utilization"] * 100
    accounts["ob_dent_30d_pct_display"] = accounts["ob_dent_30d_pct"] * 100

    invoice_lookup = accounts.drop_duplicates("buyer_lower", keep="first")
    invoice_map = invoice_lookup.set_index("buyer_lower")[["id", "am", "account_type", "partner_segment"]].to_dict("index")
    invoices = view2[view2["buyer_lower"].isin(invoice_map)].copy()
    invoices["account_id"] = invoices["buyer_lower"].map(lambda key: invoice_map[key]["id"])
    invoices["am"] = invoices["buyer_lower"].map(lambda key: invoice_map[key]["am"])
    invoices["account_type"] = invoices["buyer_lower"].map(lambda key: invoice_map[key]["account_type"])
    invoices["partner_segment"] = invoices["buyer_lower"].map(lambda key: invoice_map[key]["partner_segment"])

    month_start = pd.Timestamp(today.year, today.month, 1)
    mtd_repayments = invoices[
        invoices["Stage"].isin(REPAYMENT_STAGES)
        & invoices["settlement_date"].notna()
        & invoices["settlement_date"].between(month_start, today)
    ].copy()
    if not mtd_repayments.empty:
        mtd_repayments["repayment_amount"] = (mtd_repayments["Origination"] - mtd_repayments["Outstanding"]).clip(lower=0)
        by_account = mtd_repayments.groupby("account_id")["repayment_amount"].sum()
    else:
        by_account = pd.Series(dtype=float)
    accounts["mtd_repayments"] = accounts["id"].map(by_account).fillna(0)
    accounts["net_ob"] = accounts["ob"] - accounts["mtd_repayments"]

    return accounts, invoices, ob_pivot


def filter_team(accounts: pd.DataFrame, team_name: str) -> pd.DataFrame:
    cfg = TEAMS[team_name]
    return accounts[(accounts["partner_segment"] == cfg.segment) & (accounts["am"].isin(cfg.ams))].copy()


def apply_filters(
    accounts: pd.DataFrame,
    am: str,
    account_types: list[str],
    raw_statuses: list[str],
) -> pd.DataFrame:
    filtered = accounts.copy()
    if am != "All":
        filtered = filtered[filtered["am"] == am]
    if account_types:
        filtered = filtered[filtered["account_type"].isin(account_types)]
    if raw_statuses:
        filtered = filtered[filtered["raw_status"].isin(raw_statuses)]
    return filtered


def weighted_irr(accounts: pd.DataFrame) -> float | None:
    total_ob = accounts["ob"].sum()
    if total_ob <= 0:
        return None
    return float((accounts["irr"] * accounts["ob"]).sum() / total_ob)


def portfolio_kpis(accounts: pd.DataFrame, invoices: pd.DataFrame) -> dict[str, float | int | None]:
    open_invoices = invoices[invoices["Stage"].isin(OPEN_STAGES)] if not invoices.empty else invoices
    overdue = open_invoices[(open_invoices["dpd"] > 7) & (open_invoices["dpd"] <= 90)] if not open_invoices.empty else open_invoices
    npa = open_invoices[open_invoices["dpd"] > 90] if not open_invoices.empty else open_invoices
    total_facility = accounts["total_facility"].sum()
    total_ob = accounts["ob"].sum()
    return {
        "accounts": len(accounts),
        "total_facility": total_facility,
        "total_ob": total_ob,
        "utilization": total_ob / total_facility if total_facility > 0 else 0,
        "mtd_repayments": accounts["mtd_repayments"].sum() if "mtd_repayments" in accounts else 0,
        "net_ob": accounts["net_ob"].sum() if "net_ob" in accounts else total_ob,
        "gap_to_75": accounts["gap_to_75"].sum(),
        "zero_ob": int((accounts["ob"] < 1).sum()),
        "inactive_12m": int(
            (
                accounts["account_type"].isin(["Suspended Workable", "Workable >365"])
                | accounts["raw_status"].astype(str).str.contains("Inactive", case=False, na=False)
            )
            .where(accounts["days_since_last"].fillna(9999) <= 365, False)
            .sum()
        ),
        "overdue_ob": overdue["Outstanding"].sum() if not overdue.empty else 0,
        "npa_ob": npa["Outstanding"].sum() if not npa.empty else 0,
        "wirr": weighted_irr(accounts),
    }


def am_summary(accounts: pd.DataFrame) -> pd.DataFrame:
    if accounts.empty:
        return pd.DataFrame()
    grouped = (
        accounts.groupby("am", as_index=False)
        .agg(
            accounts=("id", "count"),
            facility=("total_facility", "sum"),
            ob=("ob", "sum"),
            repayments=("mtd_repayments", "sum"),
            gap_to_75=("gap_to_75", "sum"),
            zero_ob=("ob", lambda s: int((s < 1).sum())),
        )
        .sort_values("ob", ascending=False)
    )
    grouped["utilization"] = np.where(grouped["facility"] > 0, grouped["ob"] / grouped["facility"], 0)
    return grouped


def utilization_buckets(accounts: pd.DataFrame) -> pd.DataFrame:
    bins = [
        ("0%", accounts["utilization"] <= 0),
        ("0-25%", (accounts["utilization"] > 0) & (accounts["utilization"] < 0.25)),
        ("25-50%", (accounts["utilization"] >= 0.25) & (accounts["utilization"] < 0.50)),
        ("50-75%", (accounts["utilization"] >= 0.50) & (accounts["utilization"] < 0.75)),
        ("75-100%", (accounts["utilization"] >= 0.75) & (accounts["utilization"] <= 1)),
        (">100%", accounts["utilization"] > 1),
    ]
    return pd.DataFrame(
        {"Bucket": label, "Accounts": int(mask.sum()), "OB": accounts.loc[mask, "ob"].sum()}
        for label, mask in bins
    )


def ob_trend(ob_pivot: pd.DataFrame, account_ids: set[str]) -> pd.DataFrame:
    if ob_pivot.empty or not account_ids:
        return pd.DataFrame(columns=["date", "ob"])
    cols = [col for col in ob_pivot.columns if col in account_ids]
    if not cols:
        return pd.DataFrame(columns=["date", "ob"])
    trend = ob_pivot[cols].sum(axis=1).reset_index()
    trend.columns = ["date", "ob"]
    trend["date"] = pd.to_datetime(trend["date"])
    return trend.sort_values("date")
