import sqlite3

def init_db():
    conn = sqlite3.connect("finance_app.db")
    cursor = conn.cursor()

    # Creating tables
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Users (
            User_id INTEGER PRIMARY KEY AUTOINCREMENT,
            Name TEXT NOT NULL
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Transactions (
            Transaction_id INTEGER PRIMARY KEY AUTOINCREMENT,
            User_id INTEGER NOT NULL,
            Date TEXT NOT NULL,
            Category TEXT NOT NULL,
            Amount REAL NOT NULL,
            Type TEXT NOT NULL,
            FOREIGN KEY(User_id) REFERENCES Users(User_id)
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Portfolio_assets (
            Asset_id INTEGER PRIMARY KEY AUTOINCREMENT,
            User_id INTEGER NOT NULL,
            Asset_name TEXT NOT NULL,
            Quantity REAL NOT NULL,
            Purchase_price REAL NOT NULL,
            Current_price REAL NOT NULL,
            FOREIGN KEY(User_id) REFERENCES Users(User_id)
        )
    ''')

    cursor.execute("SELECT COUNT(*) FROM Users")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO Users (Name) VALUES ('Aarav')")
        
        sample_transactions = [
            (1, '2026-06-01', 'Salary', 50000.0, 'Income'),
            (1, '2026-06-03', 'Rent', 15000.0, 'Expense'),
            (1, '2026-06-05', 'Food', 4000.0, 'Expense')
        ]
        cursor.executemany("INSERT INTO Transactions (User_id, Date, Category, Amount, Type) VALUES (?, ?, ?, ?, ?)", sample_transactions)

        sample_portfolio = [
            (1, 'AAPL', 15.0, 180.5, 195.0),
            (1, 'TSLA', 10.0, 220.0, 210.0)
        ]
        cursor.executemany("INSERT INTO Portfolio_assets (User_id, Asset_name, Quantity, Purchase_price, Current_price) VALUES (?, ?, ?, ?, ?)", sample_portfolio)
    
    conn.commit()
    conn.close()
    print("Database initialized successfully!")

def add_user(name):
    conn = sqlite3.connect("finance_app.db")
    cursor = conn.cursor()
    cursor.execute("INSERT INTO Users (Name) VALUES (?)", (name,))
    conn.commit()
    conn.close()

def delete_user(user_id):
    """
    Delete a user and all their related data (transactions and portfolio assets).
    SQLite doesn't cascade-delete by default, so we clean up child tables manually.
    """
    conn = sqlite3.connect("finance_app.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM Transactions WHERE User_id = ?", (user_id,))
    cursor.execute("DELETE FROM Portfolio_assets WHERE User_id = ?", (user_id,))
    cursor.execute("DELETE FROM Users WHERE User_id = ?", (user_id,))
    conn.commit()
    conn.close()

def get_all_users():
    conn = sqlite3.connect("finance_app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT User_id, Name FROM Users")
    users = cursor.fetchall()
    conn.close()
    return users

def add_transaction(date, category, amount, trans_type, user_id=1):
    conn = sqlite3.connect("finance_app.db")
    cursor = conn.cursor()
    cursor.execute("INSERT INTO Transactions (User_id, Date, Category, Amount, Type) VALUES (?, ?, ?, ?, ?)", (user_id, date, category, amount, trans_type))
    conn.commit()
    conn.close()

def add_portfolio_asset(asset_name, quantity, purchase_price, current_price, user_id=1):
    conn = sqlite3.connect("finance_app.db")
    cursor = conn.cursor()
    cursor.execute("INSERT INTO Portfolio_assets (User_id, Asset_name, Quantity, Purchase_price, Current_price) VALUES (?, ?, ?, ?, ?)", (user_id, asset_name, quantity, purchase_price, current_price))
    conn.commit()
    conn.close()

def update_asset_price(asset_id, new_price):
    """Update the Current_price of a single portfolio asset by its Asset_id."""
    conn = sqlite3.connect("finance_app.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE Portfolio_assets SET Current_price = ? WHERE Asset_id = ?", (new_price, asset_id))
    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()