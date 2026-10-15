# 💰 FinTrack - Personal Finance & Portfolio Tracker with ML

A Streamlit app that tracks income, expenses and investments, **auto-categorises transactions with a
scikit-learn model**, forecasts spending, flags unusual purchases, and analyses portfolio risk.

> Add a screenshot or GIF here (Dashboard + ML Lab) - recruiters look at this first.
> Live demo: _add your Streamlit Community Cloud link_

## Features

| Page | What it does |
|------|--------------|
| **Dashboard** | KPIs, income vs expense, savings rate, spending breakdown, budget alerts, plain-language insights |
| **Transactions** | Add (with live ML category suggestion), filter, edit, delete, export; **import bank/UPI CSV** with ML categorisation, duplicate detection and human review |
| **Portfolio** | Multi-currency holdings (INR/USD/...), live prices, weighted average cost, **FIFO sells with realised P/L** |
| **Portfolio Risk** | Sharpe, Sortino, volatility, max drawdown, VaR/CVaR, correlation heatmap, **efficient-frontier optimiser** |
| **Budgets** | Monthly limits per category with progress bars and over-budget warnings |
| **AI Insights** | Expense forecast (walk-forward model selection) and anomaly detection (Isolation Forest) |
| **ML Lab** | Try the categoriser, compare models, see the confusion matrix, retrain on your own corrections |

Also: password-protected accounts (PBKDF2-SHA256), one-click demo data, automatic migration of v1 databases.

## The ML, honestly

* **Categoriser** - TF-IDF on words + character n-grams -> logistic regression (SVM and Naive Bayes compared).
  Bootstrapped on synthetic bank-statement text, then personalised with the user's own labelled
  transactions (5x sample weight). Low-confidence predictions are flagged for review.
* **Evaluation** - a random split scores ~1.0 F1 because the same merchants appear in train and test (leakage).
  Holding out whole *merchants* (GroupKFold) gives a macro-F1 around 0.5 on the synthetic benchmark - the
  realistic number for brand-new merchants. This gap is why the app learns from your corrections.
  To improve further: train on real, labelled statements.
* **Forecast** - last-month, 3-month average and linear-trend methods are compared by walk-forward MAE on
  your own history; the best one is used, with an 80% interval. One-off anomalies are excluded.
* **Anomalies** - Isolation Forest on log-amount and amount relative to the category median
  (robust z-score when there are fewer than 30 expenses).
* **Risk** - metrics use current value weights, daily rebalanced. Expected returns are historical means:
  educational, not investment advice.

## Run it

```bash
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

Sign up, then click **Load demo data** in the sidebar to see everything populated.
Docker: `docker build -t fintrack . && docker run -p 8501:8501 fintrack`

## Tests

```bash
pip install -r requirements-dev.txt
pytest -q
```
CI runs the suite on every push (`.github/workflows/ci.yml`).

## Project layout

```
app.py            router, login/signup, sidebar
config.py         categories, currency, paths
core/             database (all SQL), auth, prices (yfinance + FX), portfolio (holdings & risk),
                  analytics, importer (CSV statements), charts, demo
ml/               dataset (synthetic data), categorizer, forecast, anomaly
views/            one module per page
tests/            pytest suite
```

## Upgrading from the first version

Your existing `finance_app.db` is migrated automatically on first start (new columns added, nothing lost).
Existing users set a password the first time they log in. Holdings without an exchange suffix
(e.g. `AAPL`) are assumed to be in USD, those like `TCS.NS` in INR - check the Portfolio page and re-add
anything that is wrong.

## Known limitations / roadmap

* Realised P/L converts buy and sell legs at today's FX rate (simplification).
* SQLite is single-user-friendly; move to PostgreSQL + SQLAlchemy for real multi-user deployment.
* Next: REST API (Flask/FastAPI) with a React frontend, recurring-transaction detection, LLM "ask your finances".
