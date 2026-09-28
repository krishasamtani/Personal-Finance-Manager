# Advanced Personal Finance & Portfolio Tracker

A feature-rich web application built with **Python**, **Streamlit**, **SQLite**, and **yfinance** to manage personal transactions, track multi-user accounts, and monitor live stock and crypto investment portfolios with dynamic data visualizations.

---

## Features

- **👤 Multi-User Management:** Switch between different user profiles or create/delete user accounts securely, with independent transaction and portfolio data.
- **✍️ Transaction Tracking:** Easily record, categorize (Food, Rent, Salary, Utilities, etc.), and view income and expense logs.
- **📈 Real-Time Portfolio & Live Pricing:** Add stocks and crypto assets (using Yahoo Finance tickers like `AAPL`, `TSLA`, `BTC-USD`) and fetch real-time market prices instantly.
- **📊 Interactive Visualizations:** Clear matplotlib charts depicting expense breakdowns, income vs. expense comparisons, asset allocations, and asset-wise profit/loss.
- **🗄️ Relational Database:** Powered by SQLite with structured normalized tables for users, transactions, and portfolio assets.

---

##  Tech Stack

- **Frontend / UI:** [Streamlit](https://streamlit.io/)
- **Backend / Logic:** Python
- **Database:** SQLite (`sqlite3`)
- **Data Analysis:** Pandas, NumPy
- **Financial Data API:** `yfinance`
- **Visualization:** Matplotlib

---

##  Project Structure

```text
FinanceApp/
│
├── app.py              # Main Streamlit application interface and navigation
├── analytics.py        # Financial metrics calculation and data aggregation
├── database.py         # SQLite database initialization and CRUD operations
├── price_fetcher.py    # Live stock/crypto price fetcher using yfinance
├── visualizer.py       # Matplotlib charts generator
├── requirements.txt    # Project dependencies
└── finance_app.db      # SQLite database (auto-generated)