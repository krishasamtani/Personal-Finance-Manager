import numpy as np
import pandas as pd
import pytest

from core import portfolio


def test_max_drawdown_known_series():
    r = pd.Series([0.10, -0.50, 0.20])
    assert portfolio.max_drawdown(r) == pytest.approx(-0.5)


def test_risk_metrics_and_frontier():
    rng = np.random.default_rng(1)
    rets = pd.DataFrame(rng.normal(0.0005, 0.01, (300, 3)), columns=["A", "B", "C"])
    m = portfolio.risk_metrics(rets["A"])
    assert m["Volatility"] > 0 and m["VaR 95% (1-day)"] < 0 and m["CVaR 95% (1-day)"] <= m["VaR 95% (1-day)"]
    f = portfolio.efficient_frontier(rets, n_portfolios=500)
    assert len(f) == 500 and np.allclose(f[["A", "B", "C"]].sum(axis=1), 1)
    with pytest.raises(ValueError):
        portfolio.efficient_frontier(rets[["A"]])


def test_weights_and_portfolio_returns():
    h = pd.DataFrame({"Asset_name": ["A", "B"], "Value_INR": [300.0, 100.0]})
    w = portfolio.weights_from_holdings(h, ["A", "B"])
    assert w["A"] == pytest.approx(0.75)
    r = pd.DataFrame({"A": [0.02], "B": [0.04]})
    assert portfolio.portfolio_returns(r, w).iloc[0] == pytest.approx(0.75 * 0.02 + 0.25 * 0.04)
