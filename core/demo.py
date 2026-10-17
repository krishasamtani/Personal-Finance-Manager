"""One-click demo data so the app (and your screenshots) never look empty."""
import numpy as np
import pandas as pd

from core import database
from ml.dataset import MERCHANTS, noisy

# ticker, qty, buy price, "current" price, currency, beta to market, idiosyncratic daily vol
DEMO_ASSETS = [
    ("RELIANCE.NS", 20, 2450.0, 2610.0, "INR", 0.9, 0.011),
    ("TCS.NS", 8, 3900.0, 3720.0, "INR", 0.7, 0.010),
    ("INFY.NS", 25, 1500.0, 1610.0, "INR", 0.8, 0.012),
    ("AAPL", 6, 190.0, 232.0, "USD", 1.0, 0.012),
    ("BTC-USD", 0.05, 62000.0, 71000.0, "USD", 1.6, 0.025),
]
DEMO_BUDGETS = {"Food": 9000, "Groceries": 7000, "Entertainment": 2000, "Transport": 3500,
                "Shopping": 6000, "Health": 3000, "Travel": 8000}


def build_demo_transactions(months=12, seed=7, today=None):
    rng = np.random.default_rng(seed)
    today = pd.Timestamp(today or pd.Timestamp.today()).normalize()
    this_month = today.to_period("M")
    rows = []

    def add(day_ts, category, amount, merchant=None, exact=False):
        if day_ts > today:
            return
        m = merchant or str(rng.choice(MERCHANTS[category]))
        rows.append({"Date": day_ts.strftime("%Y-%m-%d"), "Category": category, "Amount": round(float(amount), 2),
                     "Type": "Income" if category in ("Salary", "Freelance", "Interest", "Refund") else "Expense",
                     "Description": m if exact else noisy(m, rng), "Source": "demo"})

    for k in range(months - 1, -1, -1):
        period = this_month - k
        start = period.to_timestamp()
        day = lambda d: start + pd.Timedelta(days=min(d, 27) - 1)
        add(day(1), "Salary", 80000 * (1 + 0.01 * (months - k)), "Salary Credit")
        add(day(3), "Rent", 22000, "House Rent")
        add(day(5), "Investment", 10000, "Groww SIP")
        add(day(8), "Utilities", rng.uniform(1400, 2600), "Electricity Bill MSEDCL")
        add(day(10), "Utilities", 599, "Jio Recharge", exact=True)
        add(day(15), "Entertainment", 649, "Netflix", exact=True)
        add(day(16), "Entertainment", 119, "Spotify", exact=True)
        for _ in range(int(rng.integers(14, 22))):
            add(day(int(rng.integers(1, 29))), "Food", rng.uniform(120, 650))
        for _ in range(int(rng.integers(4, 7))):
            add(day(int(rng.integers(1, 29))), "Groceries", rng.uniform(300, 1800))
        for _ in range(int(rng.integers(8, 13))):
            add(day(int(rng.integers(1, 29))), "Transport", rng.uniform(60, 450))
        for _ in range(int(rng.integers(1, 4))):
            add(day(int(rng.integers(1, 29))), "Shopping", rng.uniform(700, 4000))
        if rng.random() < 0.5:
            add(day(int(rng.integers(1, 29))), "Health", rng.uniform(300, 2500))
        if rng.random() < 0.3:
            add(day(int(rng.integers(1, 29))), "Education", rng.uniform(499, 1299))
        if rng.random() < 0.2:
            add(day(int(rng.integers(1, 29))), "Travel", rng.uniform(3000, 9000))
        if rng.random() < 0.3:
            add(day(int(rng.integers(5, 25))), "Freelance", rng.uniform(8000, 20000), "Client Payment")
        if period.month % 3 == 0:
            add(day(28), "Interest", rng.uniform(900, 1500), "Savings Interest")
        if k == 2:  # one deliberate outlier for the anomaly detector to find
            add(day(18), "Shopping", 74999, "Croma Electronics Laptop")
    return rows


def trading_days(days, today=None):
    """Exactly `days` weekdays ending on or before `today`.

    (pd.bdate_range(end=<weekend>, periods=n) silently returns n-1 dates, hence this helper.)
    """
    end = pd.Timestamp(today or pd.Timestamp.today()).normalize()
    every_day = pd.date_range(end=end, periods=days * 2)
    return every_day[every_day.dayofweek < 5][-days:]


def simulate_prices(days=260, seed=11, today=None):
    """Correlated random-walk price history ending at each demo asset's current price."""
    rng = np.random.default_rng(seed)
    dates = trading_days(days, today)
    market = rng.normal(0.0004, 0.009, days)
    out = {}
    for ticker, _, _, current, _, beta, vol in DEMO_ASSETS:
        r = beta * market + rng.normal(0.0002, vol, days)
        path = np.cumprod(1 + r)
        out[ticker] = pd.DataFrame({"Date": dates.strftime("%Y-%m-%d"), "Close": path * current / path[-1]})
    return out


def load_demo_data(user_id):
    """Insert transactions, holdings, budgets and simulated price history for a user."""
    n = database.add_transactions_bulk(user_id, build_demo_transactions())
    for ticker, qty, buy, cur, ccy, _, _ in DEMO_ASSETS:
        database.add_asset(user_id, ticker, qty, buy, cur, ccy)
    database.set_budgets(user_id, DEMO_BUDGETS)
    for ticker, hist in simulate_prices().items():
        database.save_price_history(ticker, hist)
    return n