import pytest

from core import auth, database
from tests.helpers import fresh_env


def test_register_and_login():
    fresh_env()
    uid, _ = auth.register("Asha", "secret1")
    assert uid
    assert auth.login("asha", "secret1")[0] == uid          # case-insensitive username
    assert auth.login("Asha", "wrong")[0] is None
    assert auth.register("ASHA", "another1")[0] is None      # duplicate
    assert auth.register("B", "secret1")[0] is None          # too short
    assert auth.register("Bob", "123")[0] is None            # weak password


def test_legacy_user_claims_account():
    fresh_env()
    uid = database.create_user("Aarav")                      # v1-style user without password
    assert auth.login("Aarav", "abc")[0] is None             # too short to claim
    assert auth.login("Aarav", "newpass1")[0] == uid
    assert auth.login("Aarav", "newpass1")[0] == uid
    assert auth.login("Aarav", "other")[0] is None


def test_transaction_crud_and_isolation():
    fresh_env()
    u1, u2 = database.create_user("a"), database.create_user("b")
    database.add_transaction(u1, "2026-01-05", "Food", 250, "Expense", "Swiggy")
    database.add_transactions_bulk(u2, [{"Date": "2026-01-06", "Category": "Salary", "Amount": 1000,
                                         "Type": "Income", "Description": "pay"}])
    t1 = database.get_transactions(u1)
    assert len(t1) == 1 and t1.loc[0, "Description"] == "Swiggy"
    tid = int(t1.loc[0, "Transaction_id"])
    database.update_transaction(u2, tid, Amount=1)           # wrong user -> no effect
    assert database.get_transactions(u1).loc[0, "Amount"] == 250
    database.update_transaction(u1, tid, Amount=300, Source="corrected")
    assert database.get_transactions(u1).loc[0, "Amount"] == 300
    with pytest.raises(ValueError):
        database.update_transaction(u1, tid, User_id=2)      # not whitelisted
    database.delete_transactions(u1, [tid])
    assert database.get_transactions(u1).empty
    assert len(database.get_transactions(u2)) == 1


def test_fifo_sell_and_realised_pnl():
    fresh_env()
    u = database.create_user("a")
    database.add_asset(u, "tcs.ns", 10, 100.0, 120.0, "INR")
    database.add_asset(u, "TCS.NS", 10, 200.0, 120.0, "INR")
    pnl = database.sell_asset(u, "TCS.NS", 15, 150.0, fx_rate=1.0)
    assert pnl == pytest.approx(10 * 50 + 5 * (-50))          # first lot fully, 5 units of second
    left = database.get_assets(u)
    assert len(left) == 1 and left.loc[0, "Quantity"] == pytest.approx(5)
    with pytest.raises(ValueError):
        database.sell_asset(u, "TCS.NS", 6, 150.0)
    assert len(database.get_realized_trades(u)) == 2


def test_delete_user_removes_everything():
    fresh_env()
    u = database.create_user("a")
    database.add_transaction(u, "2026-01-01", "Food", 1, "Expense")
    database.add_asset(u, "X", 1, 1, 1)
    database.set_budgets(u, {"Food": 100})
    database.delete_user(u)
    assert database.get_user(u) is None
    assert database.get_transactions(u).empty and database.get_assets(u).empty and database.get_budgets(u).empty


def test_price_history_roundtrip():
    import pandas as pd
    fresh_env()
    df = pd.DataFrame({"Date": ["2026-01-01", "2026-01-02"], "Close": [10.0, 11.0]})
    database.save_price_history("abc", df)
    wide = database.get_price_history(["ABC"])
    assert list(wide.columns) == ["ABC"] and len(wide) == 2


def test_v1_database_migrates_without_data_loss():
    import sqlite3

    import config
    from core import portfolio
    d = fresh_env()
    legacy = d / "v1.db"
    con = sqlite3.connect(legacy)
    con.executescript("""
        CREATE TABLE Users (User_id INTEGER PRIMARY KEY AUTOINCREMENT, Name TEXT NOT NULL);
        CREATE TABLE Transactions (Transaction_id INTEGER PRIMARY KEY AUTOINCREMENT, User_id INTEGER, Date TEXT,
            Category TEXT, Amount REAL, Type TEXT);
        CREATE TABLE Portfolio_assets (Asset_id INTEGER PRIMARY KEY AUTOINCREMENT, User_id INTEGER, Asset_name TEXT,
            Quantity REAL, Purchase_price REAL, Current_price REAL);
        INSERT INTO Users (Name) VALUES ('Old User');
        INSERT INTO Transactions (User_id, Date, Category, Amount, Type) VALUES (1, '2026-01-01', 'Food', 99, 'Expense');
        INSERT INTO Portfolio_assets (User_id, Asset_name, Quantity, Purchase_price, Current_price)
            VALUES (1, 'AAPL', 0, 0, 200), (1, 'AAPL', 2, 50, 200), (1, 'TCS.NS', 1, 3000, 3500);
    """)
    con.commit()
    con.close()
    config.DB_PATH = legacy
    database.init_db()
    database.init_db()                                        # idempotent
    assert len(database.get_transactions(1)) == 1
    assets = database.get_assets(1)
    assert set(assets.loc[assets["Asset_name"] == "AAPL", "Currency"]) == {"USD"}
    assert assets.loc[assets["Asset_name"] == "TCS.NS", "Currency"].iloc[0] == "INR"
    h = portfolio.build_holdings(assets, fx_lookup=lambda c: 80.0 if c == "USD" else 1.0)
    assert len(h) == 2 and h.set_index("Asset_name").loc["AAPL", "Quantity"] == 2   # zero-qty lot ignored
    assert auth.login("old user", "brandnew1")[0] == 1
