"""Pure pandas analytics on transactions (no UI, easy to unit-test)."""
from datetime import date

import numpy as np
import pandas as pd

import config
from core import database

SYM = config.CURRENCY_SYMBOL


def fetch_transactions(user_id):
    df = database.get_transactions(user_id)
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    return df.dropna(subset=["Date"]).reset_index(drop=True)


def monthly_summary(df):
    """One row per calendar month (gaps filled with zeros)."""
    cols = ["Month", "Income", "Expense", "Savings", "Savings_rate"]
    if df.empty:
        return pd.DataFrame(columns=cols)
    d = df.copy()
    d["Month"] = d["Date"].dt.to_period("M").dt.to_timestamp()
    pivot = d.pivot_table(index="Month", columns="Type", values="Amount", aggfunc="sum", fill_value=0.0)
    for col in ("Income", "Expense"):
        if col not in pivot.columns:
            pivot[col] = 0.0
    out = pivot[["Income", "Expense"]].copy()
    out.columns.name = None
    full = pd.date_range(out.index.min(), out.index.max(), freq="MS")
    out = out.reindex(full, fill_value=0.0).rename_axis("Month").reset_index()
    out["Savings"] = out["Income"] - out["Expense"]
    out["Savings_rate"] = np.where(out["Income"] > 0, out["Savings"] / out["Income"] * 100, 0.0)
    return out[cols]


def spending_by_category(df, month=None):
    """Expense totals per category; `month` is a pandas Period (None = all time)."""
    exp = df[df["Type"] == "Expense"]
    if month is not None:
        exp = exp[exp["Date"].dt.to_period("M") == month]
    out = exp.groupby("Category", as_index=False)["Amount"].sum().sort_values("Amount", ascending=False)
    return out.reset_index(drop=True)


def budget_status(df, budgets, month=None):
    """Budget vs actual spend for one month (default: the current month)."""
    cols = ["Category", "Limit", "Spent", "Pct", "Remaining", "Status"]
    if budgets.empty:
        return pd.DataFrame(columns=cols)
    month = month if month is not None else pd.Period(date.today(), "M")
    spent = spending_by_category(df, month).set_index("Category")["Amount"]
    out = budgets.rename(columns={"Monthly_limit": "Limit"}).copy()
    out["Spent"] = out["Category"].map(spent).fillna(0.0)
    out["Pct"] = out["Spent"] / out["Limit"] * 100
    out["Remaining"] = out["Limit"] - out["Spent"]
    out["Status"] = np.select([out["Pct"] > 100, out["Pct"] >= 80], ["Over", "Warning"], default="OK")
    return out[cols].sort_values("Pct", ascending=False).reset_index(drop=True)


def financial_summary(df, port_summary=None):
    income = float(df.loc[df["Type"] == "Income", "Amount"].sum())
    expense = float(df.loc[df["Type"] == "Expense", "Amount"].sum())
    port = port_summary or {"invested": 0.0, "value": 0.0, "pnl": 0.0, "pnl_pct": 0.0}
    return {"income": income, "expense": expense, "savings": income - expense,
            "savings_rate": (income - expense) / income * 100 if income > 0 else 0.0,
            "portfolio_value": port["value"], "portfolio_pnl": port["pnl"], "portfolio_pnl_pct": port["pnl_pct"]}


def generate_insights(df):
    """Plain-language observations about the most recent month."""
    if df.empty:
        return []
    out = []
    d = df.copy()
    d["P"] = d["Date"].dt.to_period("M")
    latest = d["P"].max()
    prev = latest - 1
    exp = d[d["Type"] == "Expense"]
    cur = exp[exp["P"] == latest].groupby("Category")["Amount"].sum()
    pre = exp[exp["P"] == prev].groupby("Category")["Amount"].sum()
    label = latest.strftime("%b %Y")
    if not cur.empty:
        top = cur.idxmax()
        out.append(f"Biggest expense in {label}: **{top}** ({SYM}{cur.max():,.0f}, {cur.max() / cur.sum():.0%} of spending).")
        for cat in cur.index:
            if cat in pre.index and pre[cat] > 0 and cur[cat] > 1.3 * pre[cat] and cur[cat] - pre[cat] > 1000:
                out.append(f"**{cat}** is up {cur[cat] / pre[cat] - 1:.0%} vs last month (+{SYM}{cur[cat] - pre[cat]:,.0f}).")
    row = monthly_summary(df).iloc[-1]
    if row["Income"] > 0:
        rate = row["Savings_rate"]
        verdict = "healthy" if rate >= 20 else "below the common 20% guideline"
        out.append(f"Savings rate in {label}: **{rate:.0f}%** - {verdict}.")
    return out
