# %%
# reconcile_hierarchy.py
# Python version of the TMS-to-subledger hierarchy reconciliation.
# Explodes TMS positions through a two-level hierarchy (positions -> deals ->
# client sub-accounts), reconciles to the subledger, labels every break, and
# runs two data quality checks. Mirrors the Power Query version step for step.

import pandas as pd
import numpy as np
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent   # project folder (one level up)
DATA_DIR = PROJECT_DIR / "data"
OUTPUT_DIR = PROJECT_DIR / "output"
TOLERANCE = 0.01                                        # differences under one cent are rounding

# %%
# Staging: load the three sources (like stg_TMS, stg_Hierarchy, stg_Subledger)
tms = pd.read_excel(DATA_DIR / "tms_positions.xlsx")
hierarchy = pd.read_excel(DATA_DIR / "allocation_hierarchy.xlsx")
subledger = pd.read_excel(DATA_DIR / "subledger_balances.xlsx")

# %%
# Explode level 1: split each position across the deals it funds (like int_Level1).
# Left join keeps positions with no mapping, so unmapped money is never dropped silently.
level1 = tms.merge(hierarchy, how="left", left_on="Position ID", right_on="Parent ID")
level1 = level1.drop(columns="Parent ID")
level1["Allocated"] = level1["Amount"] * level1["Share"]

# %%
# Explode level 2: split each deal across its client sub-accounts (like int_Level2).
# Same join, one level down: match on the deal instead of the position.
level2 = level1.rename(columns={"Child ID": "Deal ID", "Share": "Deal Share", "Allocated": "Deal Amount"})
level2 = level2.merge(hierarchy, how="left", left_on="Deal ID", right_on="Parent ID")
level2 = level2.drop(columns="Parent ID")
level2 = level2.rename(columns={"Child ID": "Sub-Account ID", "Share": "Client Share"})
level2["Client Amount"] = level2["Deal Amount"] * level2["Client Share"]

# %%
# Expected balances: add up every path that reaches the same client on the same day
# (like out_ExpectedBalances). Unmapped rows are removed here; Check 2 reports them.
expected = (
    level2
    .dropna(subset=["Sub-Account ID"])
    .groupby(["Value Date", "Sub-Account ID"], as_index=False)
    .agg(**{"Expected Balance": ("Client Amount", "sum")})
)

# %%
# Subledger totals: one row per client per day, with a row count
# (like int_SubledgerTotals). A Row Count above 1 means a duplicate.
actual = (
    subledger
    .groupby(["Balance Date", "Sub-Account ID"], as_index=False)
    .agg(**{
        "Actual Balance": ("Balance", "sum"),
        "SL Row Count":   ("Balance", "size"),
    })
)

# %%
# Reconciliation (like out_Reconciliation).
# Same key names on both sides, so the outer join combines them into single
# Date and Account columns (no need for the ?? step used in Power Query).
expected = expected.rename(columns={"Value Date": "Date", "Sub-Account ID": "Account"})
actual = actual.rename(columns={"Balance Date": "Date", "Sub-Account ID": "Account"})

# Outer join keeps rows missing from EITHER side
recon = expected.merge(actual, how="outer", on=["Date", "Account"])

# Actual minus expected; a missing side counts as 0 so the full amount shows
recon["Difference"] = recon["Actual Balance"].fillna(0) - recon["Expected Balance"].fillna(0)

# Label each row. Order matters: structural problems are checked before amounts,
# so a missing or duplicate row is never mislabeled as a simple balance break.
conditions = [
    recon["Expected Balance"].isna(),
    recon["Actual Balance"].isna(),
    recon["SL Row Count"] > 1,
    recon["Difference"].abs() > TOLERANCE,
]
labels = ["Subledger only", "Missing in subledger", "Duplicate in subledger", "Balance break"]
recon["Status"] = np.select(conditions, labels, default="Matched")

print("Reconciliation:", len(recon), "rows")
print(recon["Status"].value_counts().to_string())

# %%
# Check 1: shares under each parent must add up to 100% (like Check_ShareTotals).
# Round first, because decimals are stored imperfectly (0.1 + 0.2 + 0.7 can be 0.9999...).
share_totals = hierarchy.groupby("Parent ID", as_index=False)["Share"].sum()
check_share_totals = share_totals[share_totals["Share"].round(4) != 1]

print("\nCheck 1: parents whose shares don't add up to 100%")
print(check_share_totals.to_string(index=False))

# %%
# Check 2: TMS positions missing from the hierarchy (like Check_UnmappedPositions).
# ~ ... .isin(...) is a left anti join: positions with no matching Parent ID.
check_unmapped = tms[~tms["Position ID"].isin(hierarchy["Parent ID"])]

print("\nCheck 2: TMS positions with no hierarchy mapping")
print(check_unmapped[["Value Date", "Position ID", "Amount"]].to_string(index=False))

# %%
# Save the reconciliation so it can be cross-checked against Power Query
OUTPUT_DIR.mkdir(exist_ok=True)
recon.to_csv(OUTPUT_DIR / "recon_python.csv", index=False)
print("\nSaved:", len(recon), "rows to output/recon_python.csv")