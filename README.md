# Portfolio Dashboard

This app consolidates Team Nikhil's CP account view and Team Pankit's direct-sales view into one Streamlit dashboard.

## Run

```powershell
cd C:\Users\PratikPandey\scf-dashboard
streamlit run app.py
```

The existing `dashboard.py` is left intact. The unified dashboard entry point is `app.py`.

## Files

- `app.py` - Streamlit UI, team/AM filters, tabs, charts, and tables.
- `data_loader.py` - single cached `load_data()` function for Excel ingestion.
- `metrics.py` - all portfolio segmentation, KPI, repayment, utilization, and opportunity logic.

## Default Data Paths

When manual upload is off, the app loads these local files from `C:\Users\PratikPandey\Downloads`:

- `scf_am_team___view_1_with_suspension_reasons_2026-06-05T13_49_41.37721429Z.xlsx`
- `view_2_2026-06-05T13_49_21.379501371Z.xlsx`
- `us_scf___master_data___handover_date_2026-06-05T14_10_07.092355226Z.xlsx`
- `Historic OB.xlsx`
- `us_scf___daily_ob_by_accounts_2026-06-03T15_05_48.33250036Z.xlsx`

Manual uploads are available from the sidebar.

## Team Logic

- Team Nikhil: partner-backed CP accounts, excluding direct partner accounts, for Nikhil's AM list.
- Team Pankit: non-partner/direct accounts for Pankit's AM list.
- Users first select the division, then select `All Account Managers` or one AM.
- Account type and raw status filters are exposed as multiselects.

## Metric Rules

- Total facility = `Facility_Size + Overdraft_Limit`.
- Utilization = `OB / Total facility`.
- 75% target OB = `Total facility * 0.75`.
- Gap to 75% = `max(75% target OB - OB, 0)`.
- Repayments follow the Pankit-style account logic using invoice rows settled MTD:
  `max(Origination - Outstanding, 0)` for `closed`, `paid`, `received`, or `partial` stages.
- Net OB = `OB - MTD repayments`.
- Overdue OB = open invoice outstanding where `dpd > 7 and dpd <= 90`.
- NPA OB = open invoice outstanding where `dpd > 90`.
- WIRR = OB-weighted IRR.

## Validation Notes

The available Excel files contain the required Nikhil/SCF source columns. Pankit's original reference file contained precomputed React data, so the unified app derives Team Pankit's direct-team view from the same master, view 1, view 2, and OB files using the segmentation rules above.
