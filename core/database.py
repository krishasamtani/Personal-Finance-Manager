"""SQLite data-access layer. All SQL lives in this file."""
import sqlite3
from contextlib import contextmanager
from datetime import date

import pandas as pd

import config

TXN_EDITABLE = {"Date", "Category", "Amount", "Type", "Description", "Source"}


@contextmanager
def get_conn():
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def read_df(query, params=()):
    """Run a SELECT and return a DataFrame (plain connection, no Row factory)."""
    conn = sqlite3.connect(config.DB_PATH)
    try:
        return pd.read_sql_query(query, conn, params=params)
    finally:
        conn.close()


# --------------------------------------------------------------------- schema
def _ensure_column(conn, table, column, ddl):
    """Add the column if missing. Returns True when it was just added."""
    cols = [r["name"] for r in conn.execute(f"PRAGMA table_info({table})")]
    if column in cols:
        return False
    conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}")
    return True


def init_db():
    """Create tables and migrate databases created by the first version."""
    with get_conn() as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS Users (
            User_id INTEGER PRIMARY KEY AUTOINCREMENT,
            Name TEXT NOT NULL,
            Password_hash TEXT,
            Salt TEXT
        );
        CREATE TABLE IF NOT EXISTS Transactions (
            Transaction_id INTEGER PRIMARY KEY AUTOINCREMENT,
            User_id INTEGER NOT NULL,
            Date TEXT NOT NULL,
            Category TEXT NOT NULL,
            Amount REAL NOT NULL CHECK (Amount >= 0),
            Type TEXT NOT NULL CHECK (Type IN ('Income', 'Expense')),
            Description TEXT NOT NULL DEFAULT '',
            Source TEXT NOT NULL DEFAULT 'manual',
            FOREIGN KEY(User_id) REFERENCES Users(User_id)
        );
        CREATE TABLE IF NOT EXISTS Portfolio_assets (
            Asset_id INTEGER PRIMARY KEY AUTOINCREMENT,
            User_id INTEGER NOT NULL,
            Asset_name TEXT NOT NULL,
            Quantity REAL NOT NULL CHECK (Quantity > 0),
            Purchase_price REAL NOT NULL,
            Current_price REAL NOT NULL,
            Currency TEXT NOT NULL DEFAULT 'INR',
            FOREIGN KEY(User_id) REFERENCES Users(User_id)
        );
        CREATE TABLE IF NOT EXISTS Price_history (
            Ticker TEXT NOT NULL,
            Date TEXT NOT NULL,
            Close REAL NOT NULL,
            PRIMARY KEY (Ticker, Date)
        );
        CREATE TABLE IF NOT EXISTS Realized_trades (
            Trade_id INTEGER PRIMARY KEY AUTOINCREMENT,
            User_id INTEGER NOT NULL,
            Asset_name TEXT NOT NULL,
            Currency TEXT NOT NULL,
            Quantity REAL NOT NULL,
            Buy_price REAL NOT NULL,
            Sell_price REAL NOT NULL,
            Fx_rate REAL NOT NULL,
            Sell_date TEXT NOT NULL,
            Realized_pnl_inr REAL NOT NULL,
            FOREIGN KEY(User_id) REFERENCES Users(User_id)
        );
        CREATE TABLE IF NOT EXISTS Budgets (
            User_id INTEGER NOT NULL,
            Category TEXT NOT NULL,
            Monthly_limit REAL NOT NULL,
            PRIMARY KEY (User_id, Category),
            FOREIGN KEY(User_id) REFERENCES Users(User_id)
        );
        """)
        # migrations for databases created by v1
        _ensure_column(conn, "Users", "Password_hash", "TEXT")
        _ensure_column(conn, "Users", "Salt", "TEXT")
        _ensure_column(conn, "Transactions", "Description", "TEXT NOT NULL DEFAULT ''")
        _ensure_column(conn, "Transactions", "Source", "TEXT NOT NULL DEFAULT 'manual'")
        if _ensure_column(conn, "Portfolio_assets", "Currency", "TEXT NOT NULL DEFAULT 'INR'"):
            # v1 had no currency: tickers without an exchange suffix (AAPL, BTC-USD) are quoted in USD,
            # while .NS / .BO tickers stay INR.
            conn.execute("UPDATE Portfolio_assets SET Currency = 'USD' WHERE Asset_name NOT LIKE '%.%'")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_txn_user_date ON Transactions(User_id, Date)")
        try:
            conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_users_name ON Users(Name COLLATE NOCASE)")
        except sqlite3.IntegrityError:
            pass  # legacy DB already has duplicate names; the app-level check still applies


# ---------------------------------------------------------------------- users
def create_user(name, password_hash=None, salt=None):
    with get_conn() as conn:
        cur = conn.execute("INSERT INTO Users (Name, Password_hash, Salt) VALUES (?, ?, ?)",
                           (name.strip(), password_hash, salt))
        return cur.lastrowid


def get_user_by_name(name):
    with get_conn() as conn:
        return conn.execute("SELECT * FROM Users WHERE Name = ? COLLATE NOCASE", (name.strip(),)).fetchone()


def get_user(user_id):
    with get_conn() as conn:
        return conn.execute("SELECT * FROM Users WHERE User_id = ?", (user_id,)).fetchone()


def set_password(user_id, password_hash, salt):
    with get_conn() as conn:
        conn.execute("UPDATE Users SET Password_hash = ?, Salt = ? WHERE User_id = ?",
                     (password_hash, salt, user_id))


def delete_user(user_id):
    """Delete a user and every row that belongs to them."""
    with get_conn() as conn:
        for table in ("Transactions", "Portfolio_assets", "Realized_trades", "Budgets"):
            conn.execute(f"DELETE FROM {table} WHERE User_id = ?", (user_id,))
        conn.execute("DELETE FROM Users WHERE User_id = ?", (user_id,))


# --------------------------------------------------------------- transactions
def add_transaction(user_id, date_, category, amount, trans_type, description="", source="manual"):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO Transactions (User_id, Date, Category, Amount, Type, Description, Source) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (user_id, str(date_), category, float(amount), trans_type, description.strip(), source))


def add_transactions_bulk(user_id, rows):
    """rows: iterable of dicts with Date, Category, Amount, Type, Description, Source."""
    data = [(user_id, str(r["Date"])[:10], r["Category"], float(r["Amount"]), r["Type"],
             str(r.get("Description", "")).strip(), r.get("Source", "imported")) for r in rows]
    with get_conn() as conn:
        conn.executemany(
            "INSERT INTO Transactions (User_id, Date, Category, Amount, Type, Description, Source) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)", data)
    return len(data)


def get_transactions(user_id):
    return read_df(
        "SELECT Transaction_id, Date, Category, Amount, Type, Description, Source "
        "FROM Transactions WHERE User_id = ? ORDER BY Date, Transaction_id", (user_id,))


def update_transaction(user_id, transaction_id, **fields):
    bad = set(fields) - TXN_EDITABLE
    if bad:
        raise ValueError(f"Cannot update fields: {sorted(bad)}")
    if not fields:
        return
    assignments = ", ".join(f"{k} = ?" for k in fields)  # keys are whitelisted above
    with get_conn() as conn:
        conn.execute(f"UPDATE Transactions SET {assignments} WHERE Transaction_id = ? AND User_id = ?",
                     (*fields.values(), transaction_id, user_id))


def delete_transactions(user_id, ids):
    with get_conn() as conn:
        conn.executemany("DELETE FROM Transactions WHERE Transaction_id = ? AND User_id = ?",
                         [(int(i), user_id) for i in ids])


def get_labelled_descriptions(user_id):
    """Descriptions the user labelled themselves (used to personalise the ML model)."""
    return read_df(
        "SELECT Description AS description, Category AS category FROM Transactions "
        "WHERE User_id = ? AND Description <> '' AND Source IN ('manual', 'corrected')", (user_id,))


# ------------------------------------------------------------------ portfolio
def add_asset(user_id, ticker, quantity, purchase_price, current_price, currency="INR"):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO Portfolio_assets (User_id, Asset_name, Quantity, Purchase_price, Current_price, Currency) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (user_id, ticker.strip().upper(), float(quantity), float(purchase_price),
             float(current_price), currency))


def get_assets(user_id):
    return read_df(
        "SELECT Asset_id, Asset_name, Quantity, Purchase_price, Current_price, Currency "
        "FROM Portfolio_assets WHERE User_id = ? ORDER BY Asset_id", (user_id,))


def update_asset_price(user_id, ticker, new_price):
    with get_conn() as conn:
        conn.execute("UPDATE Portfolio_assets SET Current_price = ? WHERE User_id = ? AND Asset_name = ?",
                     (float(new_price), user_id, ticker.strip().upper()))


def delete_asset(user_id, asset_id):
    with get_conn() as conn:
        conn.execute("DELETE FROM Portfolio_assets WHERE Asset_id = ? AND User_id = ?", (int(asset_id), user_id))


def sell_asset(user_id, ticker, quantity, sell_price, fx_rate=1.0, sell_date=None):
    """Sell units using FIFO across buy lots. Returns realised P/L in INR.

    Simplification: both the buy and the sell leg are converted at today's FX rate.
    """
    ticker = ticker.strip().upper()
    if quantity <= 0:
        raise ValueError("Quantity must be positive")
    sell_date = str(sell_date or date.today())
    with get_conn() as conn:
        lots = conn.execute(
            "SELECT Asset_id, Quantity, Purchase_price, Currency FROM Portfolio_assets "
            "WHERE User_id = ? AND Asset_name = ? ORDER BY Asset_id", (user_id, ticker)).fetchall()
        available = sum(l["Quantity"] for l in lots)
        if quantity > available + 1e-9:
            raise ValueError(f"You only hold {available:g} units of {ticker}")
        remaining, total_pnl = float(quantity), 0.0
        for lot in lots:
            if remaining <= 1e-12:
                break
            take = min(remaining, lot["Quantity"])
            pnl_inr = (sell_price - lot["Purchase_price"]) * take * fx_rate
            conn.execute(
                "INSERT INTO Realized_trades (User_id, Asset_name, Currency, Quantity, Buy_price, Sell_price, "
                "Fx_rate, Sell_date, Realized_pnl_inr) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (user_id, ticker, lot["Currency"], take, lot["Purchase_price"], sell_price, fx_rate,
                 sell_date, pnl_inr))
            left = lot["Quantity"] - take
            if left <= 1e-9:
                conn.execute("DELETE FROM Portfolio_assets WHERE Asset_id = ?", (lot["Asset_id"],))
            else:
                conn.execute("UPDATE Portfolio_assets SET Quantity = ? WHERE Asset_id = ?", (left, lot["Asset_id"]))
            remaining -= take
            total_pnl += pnl_inr
    return total_pnl


def get_realized_trades(user_id):
    return read_df(
        "SELECT Sell_date, Asset_name, Currency, Quantity, Buy_price, Sell_price, Realized_pnl_inr "
        "FROM Realized_trades WHERE User_id = ? ORDER BY Trade_id DESC", (user_id,))


# -------------------------------------------------------------- price history
def save_price_history(ticker, df, replace=True):
    """df needs columns Date (YYYY-MM-DD) and Close."""
    ticker = ticker.strip().upper()
    with get_conn() as conn:
        if replace:
            conn.execute("DELETE FROM Price_history WHERE Ticker = ?", (ticker,))
        conn.executemany("INSERT OR REPLACE INTO Price_history (Ticker, Date, Close) VALUES (?, ?, ?)",
                         [(ticker, str(d), float(c)) for d, c in zip(df["Date"], df["Close"])])


def get_price_history(tickers):
    """Wide DataFrame: index = date, one column per ticker."""
    tickers = [t.strip().upper() for t in tickers]
    if not tickers:
        return pd.DataFrame()
    marks = ",".join("?" * len(tickers))
    df = read_df(f"SELECT Ticker, Date, Close FROM Price_history WHERE Ticker IN ({marks})", tuple(tickers))
    if df.empty:
        return pd.DataFrame()
    wide = df.pivot(index="Date", columns="Ticker", values="Close").sort_index()
    wide.index = pd.to_datetime(wide.index)
    return wide


# -------------------------------------------------------------------- budgets
def set_budgets(user_id, limits):
    """limits: {category: monthly_limit}. A limit <= 0 removes the budget."""
    with get_conn() as conn:
        for cat, limit in limits.items():
            if limit and float(limit) > 0:
                conn.execute("INSERT OR REPLACE INTO Budgets (User_id, Category, Monthly_limit) VALUES (?, ?, ?)",
                             (user_id, cat, float(limit)))
            else:
                conn.execute("DELETE FROM Budgets WHERE User_id = ? AND Category = ?", (user_id, cat))


def get_budgets(user_id):
    return read_df("SELECT Category, Monthly_limit FROM Budgets WHERE User_id = ?", (user_id,))
