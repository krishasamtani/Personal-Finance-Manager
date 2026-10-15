"""Holdings aggregation (multi-currency) and portfolio risk analytics."""
import numpy as np
import pandas as pd

from core import prices

TRADING_DAYS = 252
HOLDING_COLS = ["Asset_name", "Currency", "Quantity", "Avg_cost", "Current_price", "FX",
                "Invested_INR", "Value_INR", "PnL_INR", "PnL_pct"]


def build_holdings(assets, fx_lookup=None):
    """Aggregate buy lots into one row per asset, converted to INR."""
    assets = assets[assets["Quantity"] > 0] if not assets.empty else assets  # v1 allowed zero-quantity lots
    if assets.empty:
        return pd.DataFrame(columns=HOLDING_COLS)
    fx_lookup = fx_lookup or prices.get_fx_rate
    a = assets[assets["Quantity"] > 0].sort_values("Asset_id").copy()  # ignore empty lots from old data
    if a.empty:
        return pd.DataFrame(columns=HOLDING_COLS)
    a["Invested"] = a["Quantity"] * a["Purchase_price"]
    g = a.groupby(["Asset_name", "Currency"], as_index=False).agg(
        Quantity=("Quantity", "sum"), Invested=("Invested", "sum"), Current_price=("Current_price", "last"))
    g["Avg_cost"] = g["Invested"] / g["Quantity"]
    g["FX"] = g["Currency"].map(fx_lookup).astype(float)
    g["Invested_INR"] = g["Invested"] * g["FX"]
    g["Value_INR"] = g["Quantity"] * g["Current_price"] * g["FX"]
    g["PnL_INR"] = g["Value_INR"] - g["Invested_INR"]
    g["PnL_pct"] = np.where(g["Invested_INR"] > 0, g["PnL_INR"] / g["Invested_INR"] * 100, 0.0)
    return g[HOLDING_COLS]


def portfolio_summary(holdings):
    invested = float(holdings["Invested_INR"].sum()) if not holdings.empty else 0.0
    value = float(holdings["Value_INR"].sum()) if not holdings.empty else 0.0
    pnl = value - invested
    return {"invested": invested, "value": value, "pnl": pnl,
            "pnl_pct": (pnl / invested * 100) if invested > 0 else 0.0}


# ----------------------------------------------------------------------- risk
def returns_from_prices(price_df):
    """Daily simple returns on the dates where every asset has a price."""
    return price_df.sort_index().dropna().pct_change().dropna()


def weights_from_holdings(holdings, tickers):
    """Current-value weights for the given tickers (sums to 1)."""
    v = holdings.groupby("Asset_name")["Value_INR"].sum().reindex(tickers).fillna(0.0)
    total = v.sum()
    return v / total if total > 0 else pd.Series(1.0 / len(tickers), index=tickers)


def portfolio_returns(returns, weights):
    """Daily returns of a constant-weight (daily rebalanced) portfolio."""
    w = weights.reindex(returns.columns).fillna(0.0)
    return (returns * w).sum(axis=1)


def max_drawdown(returns):
    wealth = (1 + returns).cumprod()
    return float((wealth / wealth.cummax() - 1).min())


def risk_metrics(returns, rf=0.065):
    """Annualised risk/return summary of a daily return series (fractions, not %)."""
    n = len(returns)
    if n < 2:
        raise ValueError("Need at least two return observations")
    ann_ret = float((1 + returns).prod() ** (TRADING_DAYS / n) - 1)
    ann_vol = float(returns.std(ddof=1) * np.sqrt(TRADING_DAYS))
    downside = float(np.sqrt(np.mean(np.minimum(returns, 0) ** 2)) * np.sqrt(TRADING_DAYS))
    var95 = float(np.percentile(returns, 5))
    tail = returns[returns <= var95]
    return {
        "Annual return": ann_ret,
        "Volatility": ann_vol,
        "Sharpe ratio": (ann_ret - rf) / ann_vol if ann_vol > 0 else float("nan"),
        "Sortino ratio": (ann_ret - rf) / downside if downside > 0 else float("nan"),
        "Max drawdown": max_drawdown(returns),
        "VaR 95% (1-day)": var95,
        "CVaR 95% (1-day)": float(tail.mean()) if len(tail) else var95,
    }


def efficient_frontier(returns, n_portfolios=5000, rf=0.065, seed=42):
    """Monte-Carlo sample of long-only portfolios (random weights summing to 1)."""
    k = returns.shape[1]
    if k < 2:
        raise ValueError("Need at least two assets")
    rng = np.random.default_rng(seed)
    w = rng.dirichlet(np.ones(k), size=n_portfolios)
    mu = returns.mean().values * TRADING_DAYS
    cov = returns.cov().values * TRADING_DAYS
    rets = w @ mu
    vols = np.sqrt(np.einsum("ij,jk,ik->i", w, cov, w))
    out = pd.DataFrame(w, columns=returns.columns)
    out["Return"], out["Volatility"] = rets, vols
    out["Sharpe"] = (rets - rf) / vols
    return out
