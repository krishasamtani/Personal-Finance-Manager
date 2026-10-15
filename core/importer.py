"""Turn a messy bank/UPI statement CSV into a clean transactions table."""
from collections import Counter

import numpy as np
import pandas as pd

_ALIASES = {
    "date": ["date", "txn date", "transaction date", "value date", "posting date"],
    "description": ["description", "narration", "particulars", "details", "remarks", "transaction details"],
    "amount": ["amount", "amt", "transaction amount"],
    "debit": ["debit", "withdrawal", "withdrawals", "debit amount", "dr"],
    "credit": ["credit", "deposit", "deposits", "credit amount", "cr"],
    "type": ["type", "dr/cr", "cr/dr", "transaction type"],
}


def _find(cols, key):
    for alias in _ALIASES[key]:
        if alias in cols:
            return cols[alias]
    return None


def _to_num(s):
    return pd.to_numeric(s.astype(str).str.replace(r"[^\d.\-]", "", regex=True), errors="coerce")


def _parse_dates(s):
    iso = pd.to_datetime(s, format="ISO8601", errors="coerce")
    if iso.notna().mean() >= 0.9:
        return iso
    return pd.to_datetime(s, dayfirst=True, errors="coerce", format="mixed")


def normalize_statement(raw):
    """Returns DataFrame[Date, Description, Amount, Type]. Raises ValueError on unusable input.

    Accepted layouts: Debit/Credit columns, Amount + Type column, or a signed Amount
    (negative = expense, positive = income).
    """
    cols = {str(c).strip().lower(): c for c in raw.columns}
    c_date, c_desc = _find(cols, "date"), _find(cols, "description")
    if c_date is None or c_desc is None:
        raise ValueError("The CSV needs a Date column and a Description (or Narration) column.")
    out = pd.DataFrame({"Date": _parse_dates(raw[c_date]),
                        "Description": raw[c_desc].fillna("").astype(str).str.strip()})
    c_debit, c_credit = _find(cols, "debit"), _find(cols, "credit")
    c_amt, c_type = _find(cols, "amount"), _find(cols, "type")
    zero = pd.Series(0.0, index=raw.index)
    if c_debit is not None or c_credit is not None:
        debit = _to_num(raw[c_debit]).fillna(0.0) if c_debit is not None else zero
        credit = _to_num(raw[c_credit]).fillna(0.0) if c_credit is not None else zero
        out["Amount"] = credit.where(credit > 0, debit)
        out["Type"] = np.where(credit > 0, "Income", "Expense")
    elif c_amt is not None:
        amt = _to_num(raw[c_amt])
        if c_type is not None:
            t = raw[c_type].astype(str).str.strip().str.lower()
            out["Type"] = np.where(t.str.startswith(("c", "i")), "Income", "Expense")
        else:
            out["Type"] = np.where(amt > 0, "Income", "Expense")
        out["Amount"] = amt.abs()
    else:
        raise ValueError("Couldn't find an Amount column (or Debit/Credit columns).")
    out = out.dropna(subset=["Date", "Amount"])
    return out[out["Amount"] > 0].reset_index(drop=True)


def _key(d, amount, desc):
    return (pd.Timestamp(d).strftime("%Y-%m-%d"), round(float(amount), 2), str(desc).strip().lower())


def drop_existing(new, existing):
    """Remove rows already stored (same date, amount, description). Counts duplicates properly."""
    seen = Counter(_key(d, a, x) for d, a, x in zip(existing["Date"], existing["Amount"], existing["Description"]))
    keep = []
    for d, a, x in zip(new["Date"], new["Amount"], new["Description"]):
        k = _key(d, a, x)
        if seen[k] > 0:
            seen[k] -= 1
            keep.append(False)
        else:
            keep.append(True)
    return new[keep]
