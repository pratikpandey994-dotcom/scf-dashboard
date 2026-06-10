from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st


DOWNLOADS = Path.home() / "Downloads"

DEFAULT_FILES = {
    "view1": DOWNLOADS / "scf_am_team___view_1_with_suspension_reasons_2026-06-05T13_49_41.37721429Z.xlsx",
    "view2": DOWNLOADS / "view_2_2026-06-05T13_49_21.379501371Z.xlsx",
    "master": DOWNLOADS / "us_scf___master_data___handover_date_2026-06-05T14_10_07.092355226Z.xlsx",
    "historic_ob": DOWNLOADS / "Historic OB.xlsx",
    "current_ob": DOWNLOADS / "us_scf___daily_ob_by_accounts_2026-06-03T15_05_48.33250036Z.xlsx",
}


def norm_id(value: Any) -> str:
    if pd.isna(value):
        return ""
    text = str(value).replace(",", "").strip()
    return text[:-2] if text.endswith(".0") else text


def _read_excel(source: Any) -> pd.DataFrame:
    if source is None:
        return pd.DataFrame()
    if hasattr(source, "seek"):
        source.seek(0)
    return pd.read_excel(source)


def _resolve_source(uploaded: Any, default_path: Path) -> Any:
    if uploaded is not None:
        return uploaded
    return default_path if default_path.exists() else None


def _to_number(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    for column in columns:
        if column not in df.columns:
            df[column] = 0
        df[column] = pd.to_numeric(df[column], errors="coerce").fillna(0)
    return df


def _to_datetime(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    for column in columns:
        if column not in df.columns:
            df[column] = pd.NaT
        df[column] = pd.to_datetime(df[column], errors="coerce")
    return df


def _load_view1(source: Any) -> pd.DataFrame:
    df = _read_excel(source)
    required = {"importer_user_id", "AM_Name"}
    missing = sorted(required - set(df.columns))
    if missing:
        raise ValueError(f"View 1 is missing required column(s): {', '.join(missing)}")

    df["importer_user_id"] = df["importer_user_id"].apply(norm_id)
    df["AM_Name"] = df["AM_Name"].astype(str).str.strip()
    if "utilization_status" not in df.columns:
        df["utilization_status"] = ""
    df["utilization_status"] = df["utilization_status"].astype(str).str.strip().str.lower()
    _to_number(df, ["Facility_Size", "Outstanding_Balance", "overdraft_limit", "Signed-up IRR"])
    _to_datetime(df, ["First_Disbursed_Date", "Last_Disbursed_Date"])
    return df.set_index("importer_user_id", drop=False)


def _load_view2(source: Any) -> pd.DataFrame:
    df = _read_excel(source)
    required = {"Buyer", "Stage", "Origination", "Outstanding"}
    missing = sorted(required - set(df.columns))
    if missing:
        raise ValueError(f"View 2 is missing required column(s): {', '.join(missing)}")

    df["Buyer"] = df["Buyer"].astype(str).str.strip()
    df["buyer_lower"] = df["Buyer"].str.casefold()
    df["Stage"] = df["Stage"].astype(str).str.strip().str.lower()
    _to_number(df, ["Origination", "Outstanding", "dpd", "payment_total_usd"])
    _to_datetime(df, ["disbursed_date", "settlement_date", "due_date_of_invoice"])
    return df


def _load_master(source: Any) -> pd.DataFrame:
    df = _read_excel(source)
    required = {"Buyer_ID", "Buyer", "AM", "Partner", "Team", "Broad_Account_Status", "Account_Status"}
    missing = sorted(required - set(df.columns))
    if missing:
        raise ValueError(f"Master data is missing required column(s): {', '.join(missing)}")

    df["Buyer_ID"] = df["Buyer_ID"].apply(norm_id)
    df["Buyer"] = df["Buyer"].astype(str).str.strip()
    df["buyer_lower"] = df["Buyer"].str.casefold()
    df["AM"] = df["AM"].astype(str).str.strip()
    for column in ["Partner", "Team", "Broad_Account_Status", "Account_Status"]:
        df[column] = df[column].astype(str).str.strip()
    _to_number(df, ["Facility_Size", "Overdraft_Limit", "OB", "Signed_up_IRR"])
    _to_datetime(df, ["First_Disbursed_Date", "Last_Disbursed_Date"])
    return df


def _load_ob(source: Any) -> pd.DataFrame:
    if source is None:
        return pd.DataFrame(columns=["importer_user_id", "ob_date", "ob"])
    df = _read_excel(source)
    required = {"importer_user_id", "ob_date", "ob"}
    missing = sorted(required - set(df.columns))
    if missing:
        raise ValueError(f"OB history is missing required column(s): {', '.join(missing)}")
    df["importer_user_id"] = df["importer_user_id"].apply(norm_id)
    df["ob_date"] = pd.to_datetime(df["ob_date"], errors="coerce")
    df["ob"] = pd.to_numeric(df["ob"], errors="coerce").fillna(0)
    return df.dropna(subset=["ob_date"])


@st.cache_data(show_spinner=False)
def load_data(
    view1_file: Any = None,
    view2_file: Any = None,
    master_file: Any = None,
    historic_ob_file: Any = None,
    current_ob_file: Any = None,
) -> dict[str, pd.DataFrame]:
    """Load every Excel input through a single cached entry point."""
    view1_source = _resolve_source(view1_file, DEFAULT_FILES["view1"])
    view2_source = _resolve_source(view2_file, DEFAULT_FILES["view2"])
    master_source = _resolve_source(master_file, DEFAULT_FILES["master"])
    hist_source = _resolve_source(historic_ob_file, DEFAULT_FILES["historic_ob"])
    curr_source = _resolve_source(current_ob_file, DEFAULT_FILES["current_ob"])

    missing = [
        name
        for name, source in {
            "View 1": view1_source,
            "View 2": view2_source,
            "Master": master_source,
        }.items()
        if source is None
    ]
    if missing:
        raise FileNotFoundError(f"Missing required file(s): {', '.join(missing)}")

    historic_ob = _load_ob(hist_source)
    current_ob = _load_ob(curr_source)
    return {
        "view1": _load_view1(view1_source),
        "view2": _load_view2(view2_source),
        "master": _load_master(master_source),
        "ob_history": pd.concat([historic_ob, current_ob], ignore_index=True),
    }
