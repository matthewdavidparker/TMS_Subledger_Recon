"""
make_data.py
Generates synthetic data for the TMS-to-subledger hierarchy reconciliation project.

Three files are written to a data/ folder next to this script:
  tms_positions.xlsx        top level: what the treasury management system (TMS) holds
  allocation_hierarchy.xlsx the "bill of materials": how each position splits down two levels
  subledger_balances.xlsx   bottom level: client sub-account balances in the subledger

A few problems are planted on purpose (see answer_key/answer_key.csv).
All banks, deals, and accounts are fictional.
"""

from datetime import date, timedelta
from pathlib import Path
import random

import pandas as pd

random.seed(7)

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"
KEY = HERE / "answer_key"
DATA.mkdir(exist_ok=True)
KEY.mkdir(exist_ok=True)

# ---------------------------------------------------------------------------
# Level 0: TMS positions (like the six bike models)
# ---------------------------------------------------------------------------
positions = [
    # Position ID,     Bank,                  Instrument,       Base amount
    ("DDA-ATLAS-001",  "Atlas National Bank", "Demand Deposit", 42_000_000),
    ("DDA-ATLAS-002",  "Atlas National Bank", "Demand Deposit", 18_500_000),
    ("MMF-HARBOR",     "Harbor Funds",        "Money Market",   65_000_000),
    ("DDA-PINE-001",   "Pinecrest Bank",      "Demand Deposit", 27_250_000),
    ("TD-SUMMIT-90",   "Summit Trust",        "Time Deposit",   50_000_000),
    ("DDA-RIVER-001",  "Riverbend Bank",      "Demand Deposit", 33_800_000),
]

# ---------------------------------------------------------------------------
# The hierarchy (TRUE shares). Parent -> Child -> Share of the parent's balance.
# Level 0 -> 1: position splits across deals (a deal can be funded by several positions)
# Level 1 -> 2: deal splits across client sub-accounts (a client can sit in several deals)
# ---------------------------------------------------------------------------
true_edges = [
    # Positions -> Deals
    ("DDA-ATLAS-001", "DEAL-A", 0.60), ("DDA-ATLAS-001", "DEAL-B", 0.40),
    ("DDA-ATLAS-002", "DEAL-C", 1.00),
    ("MMF-HARBOR",    "DEAL-A", 0.25), ("MMF-HARBOR", "DEAL-D", 0.45), ("MMF-HARBOR", "DEAL-E", 0.30),
    ("DDA-PINE-001",  "DEAL-F", 0.70), ("DDA-PINE-001", "DEAL-G", 0.30),
    ("TD-SUMMIT-90",  "DEAL-D", 0.50), ("TD-SUMMIT-90", "DEAL-H", 0.50),
    ("DDA-RIVER-001", "DEAL-G", 0.20), ("DDA-RIVER-001", "DEAL-H", 0.35), ("DDA-RIVER-001", "DEAL-E", 0.45),
    # Deals -> Client sub-accounts
    ("DEAL-A", "CL-1001", 0.50), ("DEAL-A", "CL-1002", 0.30), ("DEAL-A", "CL-1003", 0.20),
    ("DEAL-B", "CL-1004", 0.65), ("DEAL-B", "CL-1007", 0.35),
    ("DEAL-C", "CL-1005", 0.40), ("DEAL-C", "CL-1006", 0.60),
    ("DEAL-D", "CL-1008", 0.25), ("DEAL-D", "CL-1009", 0.25), ("DEAL-D", "CL-1010", 0.50),
    ("DEAL-E", "CL-1011", 0.55), ("DEAL-E", "CL-1012", 0.45),
    ("DEAL-F", "CL-1013", 0.80), ("DEAL-F", "CL-1007", 0.20),
    ("DEAL-G", "CL-1014", 0.33), ("DEAL-G", "CL-1015", 0.67),
    ("DEAL-H", "CL-1016", 0.10), ("DEAL-H", "CL-1017", 0.45), ("DEAL-H", "CL-1018", 0.45),
]

# ---------------------------------------------------------------------------
# Dates: 10 business days
# ---------------------------------------------------------------------------
start = date(2026, 3, 2)
dates = [start + timedelta(days=i) for i in range(14)]
dates = [d for d in dates if d.weekday() < 5][:10]

# ---------------------------------------------------------------------------
# TMS balances: small random daily movement around each base amount
# ---------------------------------------------------------------------------
tms_rows = []
for pid, bank, inst, base in positions:
    amt = base
    for d in dates:
        amt = round(amt * (1 + random.uniform(-0.02, 0.02)), 2)
        tms_rows.append({"Value Date": d, "Position ID": pid, "Bank": bank,
                         "Instrument Type": inst, "Currency": "USD", "Amount": amt})

# PLANTED: a new position appears in the TMS but was never added to the hierarchy
for d in dates[-2:]:
    tms_rows.append({"Value Date": d, "Position ID": "TBILL-NEW", "Bank": "Summit Trust",
                     "Instrument Type": "Treasury Bill", "Currency": "USD", "Amount": 5_000_000.00})

tms = pd.DataFrame(tms_rows)

# ---------------------------------------------------------------------------
# Subledger: explode each position through the TRUE hierarchy to the client level
# ---------------------------------------------------------------------------
children = {}
for p, c, s in true_edges:
    children.setdefault(p, []).append((c, s))


def explode(node, amount, out):
    """Push an amount down the tree; only leaves (no children) collect it."""
    if node not in children:
        out[node] = out.get(node, 0) + amount
        return
    for child, share in children[node]:
        explode(child, amount * share, out)


sub_rows = []
for d in dates:
    leaf_totals = {}
    day = tms[(tms["Value Date"] == d) & (tms["Position ID"] != "TBILL-NEW")]
    for _, r in day.iterrows():
        explode(r["Position ID"], r["Amount"], leaf_totals)
    for acct in sorted(leaf_totals):
        sub_rows.append({"Balance Date": d, "Sub-Account ID": acct,
                         "Client Name": "Client " + acct[3:], "Balance": round(leaf_totals[acct], 2)})

sub = pd.DataFrame(sub_rows)

# PLANTED: missing row
miss = (sub["Balance Date"] == dates[3]) & (sub["Sub-Account ID"] == "CL-1009")
sub = sub[~miss]

# PLANTED: wrong amount (+1,000.00)
wrong = (sub["Balance Date"] == dates[6]) & (sub["Sub-Account ID"] == "CL-1015")
sub.loc[wrong, "Balance"] = sub.loc[wrong, "Balance"] + 1000

# PLANTED: duplicate row
dup = sub[(sub["Balance Date"] == dates[7]) & (sub["Sub-Account ID"] == "CL-1003")]
sub = pd.concat([sub, dup])

# PLANTED: orphan sub-account that is not in the hierarchy
orphan = pd.DataFrame([{"Balance Date": d, "Sub-Account ID": "CL-1099",
                        "Client Name": "Client 1099", "Balance": 12_500.00} for d in dates])
sub = pd.concat([sub, orphan]).sort_values(["Balance Date", "Sub-Account ID"]).reset_index(drop=True)

# ---------------------------------------------------------------------------
# Hierarchy file as published: PLANTED share error (CL-1012 0.45 keyed as 0.44)
# ---------------------------------------------------------------------------
pub_edges = [(p, c, 0.44 if (p, c) == ("DEAL-E", "CL-1012") else s) for p, c, s in true_edges]
hier = pd.DataFrame(pub_edges, columns=["Parent ID", "Child ID", "Share"])
hier = hier.sample(frac=1, random_state=3).reset_index(drop=True)  # shuffled, like a real export

# ---------------------------------------------------------------------------
# Write files
# ---------------------------------------------------------------------------
tms.to_excel(DATA / "tms_positions.xlsx", sheet_name="Positions", index=False)
hier.to_excel(DATA / "allocation_hierarchy.xlsx", sheet_name="Hierarchy", index=False)
sub.to_excel(DATA / "subledger_balances.xlsx", sheet_name="Balances", index=False)

key = pd.DataFrame([
    ("Hierarchy", "DEAL-E shares sum to 99%: CL-1012 keyed as 0.44 instead of 0.45", "CL-1012 short every day"),
    ("TMS", "TBILL-NEW has no hierarchy mapping", f"{dates[-2]} and {dates[-1]}: $5,000,000 unallocated"),
    ("Subledger", "Missing row", f"CL-1009 on {dates[3]}"),
    ("Subledger", "Wrong amount (+1,000.00)", f"CL-1015 on {dates[6]}"),
    ("Subledger", "Duplicate row", f"CL-1003 on {dates[7]}"),
    ("Subledger", "Orphan sub-account not in hierarchy", "CL-1099 every day, $12,500"),
], columns=["Source", "Planted issue", "Where it shows up"])
key.to_csv(KEY / "answer_key.csv", index=False)

print(f"TMS rows: {len(tms)}  Hierarchy rows: {len(hier)}  Subledger rows: {len(sub)}")
print(f"Dates: {dates[0]} to {dates[-1]}")
