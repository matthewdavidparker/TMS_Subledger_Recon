# %%
# crosscheck.py
# Confirms the Python and Power Query reconciliations produce the same results:
# same rows, same amounts (within one cent), and the same status label on every row.

import pandas as pd
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent   # project folder (one level up)
OUTPUT_DIR = PROJECT_DIR / "output"
TOLERANCE = 0.01                                        # amounts within one cent count as equal


def to_number(series):
    """Turn text like '$1,234.50' or '(1,234.50)' into a number; blanks stay blank."""
    text = series.astype(str).str.strip()
    negative = text.str.startswith("(")                       # accounting-style negatives
    cleaned = text.str.replace(r"[$,()]", "", regex=True)      # strip $ , ( )
    numbers = pd.to_numeric(cleaned, errors="coerce")          # anything else becomes blank
    return numbers.where(~negative, -numbers)


# %%
# Load both outputs and keep the same columns, with the same types
cols = ["Date", "Account", "Expected Balance", "Actual Balance", "Difference", "Status"]

py = pd.read_csv(OUTPUT_DIR / "recon_python.csv")[cols]
pq = pd.read_csv(OUTPUT_DIR / "recon_powerquery.csv")[cols]

for df in (py, pq):
    df["Date"] = pd.to_datetime(df["Date"], format="mixed").dt.date   # 3/2/2026 and 2026-03-02 both work
    for c in ["Expected Balance", "Actual Balance", "Difference"]:
        df[c] = to_number(df[c])

print("Python rows:      ", len(py))
print("Power Query rows: ", len(pq))


# %%
# Line the two up on date + account. Outer join keeps rows found in only one file.
both = py.merge(pq, on=["Date", "Account"], how="outer",
                suffixes=(" PY", " PQ"), indicator=True)

only_one = both[both["_merge"] != "both"]


def differs(col):
    """True where the two versions disagree: one side blank, or amounts more than a cent apart."""
    a, b = both[f"{col} PY"], both[f"{col} PQ"]
    one_blank = a.isna() != b.isna()                  # blank on one side only
    too_far = (a - b).abs() > TOLERANCE               # both have amounts, but they differ
    return one_blank | too_far


amount_breaks = both[differs("Expected Balance") | differs("Actual Balance") | differs("Difference")]
status_breaks = both[both["Status PY"] != both["Status PQ"]]

print()
print("Matched rows:        ", (both["_merge"] == "both").sum())
print("Rows in only one:    ", len(only_one))
print("Amount differences:  ", len(amount_breaks))
print("Status differences:  ", len(status_breaks))
print()
if only_one.empty and amount_breaks.empty and status_breaks.empty:
    print("RECONCILED: Python and Power Query outputs match (within $0.01).")
else:
    print("BREAKS FOUND. Open only_one, amount_breaks, or status_breaks in Data Wrangler to investigate.")