import pandas as pd
import pytest

from core import analytics, importer, portfolio


def _tx():
    return pd.DataFrame({
        "Date": pd.to_datetime(["2026-01-05", "2026-01-20", "2026-03-02", "2026-03-10"]),
        "Type": ["Income", "Expense", "Income", "Expense"],
        "Category": ["Salary", "Food", "Salary", "Food"],
        "Amount": [1000.0, 200.0, 1000.0, 500.0],
    })


def test_monthly_summary_fills_gap_months():
    m = analytics.monthly_summary(_tx())
    assert len(m) == 3                                        # Jan, Feb (gap), Mar
    assert m.loc[1, "Income"] == 0 and m.loc[1, "Expense"] == 0
    assert m.loc[0, "Savings"] == 800 and m.loc[0, "Savings_rate"] == pytest.approx(80)


def test_budget_status():
    budgets = pd.DataFrame({"Category": ["Food", "Rent"], "Monthly_limit": [400.0, 1000.0]})
    s = analytics.budget_status(_tx(), budgets, month=pd.Period("2026-03", "M")).set_index("Category")
    assert s.loc["Food", "Status"] == "Over" and s.loc["Food", "Spent"] == 500
    assert s.loc["Rent", "Status"] == "OK"


def test_holdings_multicurrency():
    assets = pd.DataFrame({"Asset_id": [1, 2], "Asset_name": ["AAPL", "AAPL"], "Quantity": [2.0, 2.0],
                           "Purchase_price": [100.0, 200.0], "Current_price": [150.0, 150.0], "Currency": ["USD"] * 2})
    h = portfolio.build_holdings(assets, fx_lookup=lambda c: 80.0)
    r = h.iloc[0]
    assert r["Quantity"] == 4 and r["Avg_cost"] == pytest.approx(150)
    assert r["Value_INR"] == pytest.approx(4 * 150 * 80) and r["PnL_INR"] == pytest.approx(0)


def test_normalize_statement_layouts():
    signed = pd.DataFrame({"Date": ["01/02/2026", "02/02/2026"], "Narration": ["Swiggy", "Salary"], "Amount": ["-1,250.50", "50000"]})
    n = importer.normalize_statement(signed)
    assert list(n["Type"]) == ["Expense", "Income"] and n.loc[0, "Amount"] == pytest.approx(1250.5)
    assert n.loc[0, "Date"] == pd.Timestamp("2026-02-01")       # day-first
    dc = pd.DataFrame({"Date": ["2026-02-01", "2026-02-02"], "Description": ["a", "b"], "Debit": [100, None], "Credit": [None, 900]})
    d = importer.normalize_statement(dc)
    assert list(d["Type"]) == ["Expense", "Income"] and list(d["Amount"]) == [100, 900]
    with pytest.raises(ValueError):
        importer.normalize_statement(pd.DataFrame({"foo": [1]}))


def test_drop_existing_counts_duplicates():
    new = pd.DataFrame({"Date": pd.to_datetime(["2026-01-01"] * 2), "Amount": [50.0, 50.0], "Description": ["Chai", "Chai"]})
    existing = pd.DataFrame({"Date": pd.to_datetime(["2026-01-01"]), "Amount": [50.0], "Description": ["chai"]})
    assert len(importer.drop_existing(new, existing)) == 1       # one already stored, one genuinely new
