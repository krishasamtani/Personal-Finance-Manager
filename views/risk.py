import pandas as pd
import streamlit as st

from core import charts, database, portfolio, prices
from views._ui import show_fig

PCT_KEYS = ["Annual return", "Volatility", "Max drawdown", "VaR 95% (1-day)", "CVaR 95% (1-day)"]


def render(user_id):
    st.title("🛡️ Portfolio Risk & Optimisation")
    holdings = portfolio.build_holdings(database.get_assets(user_id))
    if holdings.empty:
        st.info("Add some holdings first (or load demo data from the sidebar).")
        return
    tickers = holdings["Asset_name"].tolist()
    rf = st.number_input("Risk-free rate (% per year)", 0.0, 20.0, 6.5, 0.1) / 100
    if st.button("⬇️ Download 1-year price history"):
        for t in tickers:
            hist = prices.fetch_history(t)
            if hist.empty:
                st.warning(f"No history for {t}")
            else:
                database.save_price_history(t, hist)
        st.success("History updated.")
    st.caption("Demo data ships with *simulated* prices; click the button above to replace them with real history.")

    hist = database.get_price_history(tickers)
    if hist.empty or len(hist) < 30:
        st.info("Not enough price history yet. Click the download button.")
        return
    missing = [t for t in tickers if t not in hist.columns]
    if missing:
        st.warning(f"No history for: {', '.join(missing)} (excluded from the analysis).")
    returns = portfolio.returns_from_prices(hist)
    if len(returns) < 20:
        st.info("The assets share too few trading days to analyse.")
        return
    weights = portfolio.weights_from_holdings(holdings, list(returns.columns))
    port = portfolio.portfolio_returns(returns, weights)
    m = portfolio.risk_metrics(port, rf)

    cols = st.columns(4)
    cols[0].metric("Annual return", f"{m['Annual return']:.1%}")
    cols[1].metric("Volatility", f"{m['Volatility']:.1%}")
    cols[2].metric("Sharpe ratio", f"{m['Sharpe ratio']:.2f}")
    cols[3].metric("Max drawdown", f"{m['Max drawdown']:.1%}")
    cols = st.columns(3)
    cols[0].metric("Sortino ratio", f"{m['Sortino ratio']:.2f}")
    cols[1].metric("1-day VaR (95%)", f"{m['VaR 95% (1-day)']:.2%}")
    cols[2].metric("1-day CVaR (95%)", f"{m['CVaR 95% (1-day)']:.2%}")

    tab_perf, tab_corr, tab_opt = st.tabs(["Performance", "Correlation", "Optimiser"])
    with tab_perf:
        show_fig(charts.cumulative_returns(returns, port))
        show_fig(charts.drawdown_chart(port))
        per_asset = pd.DataFrame({t: portfolio.risk_metrics(returns[t], rf) for t in returns.columns}).T
        shown = per_asset.copy()
        for k in PCT_KEYS:
            shown[k] = (shown[k] * 100).round(2)
        st.dataframe(shown.round(2))
        st.caption("Percent columns are in %. Metrics use the portfolio's current value weights, rebalanced daily.")
    with tab_corr:
        if returns.shape[1] < 2:
            st.info("Need at least two assets.")
        else:
            show_fig(charts.correlation_heatmap(returns))
            st.caption("Low or negative correlation between holdings = better diversification.")
    with tab_opt:
        if returns.shape[1] < 2:
            st.info("Need at least two assets.")
        else:
            frontier = portfolio.efficient_frontier(returns, rf=rf)
            best, low = frontier.loc[frontier["Sharpe"].idxmax()], frontier.loc[frontier["Volatility"].idxmin()]
            ann_mu = float(returns.mean().values @ weights.reindex(returns.columns).values * portfolio.TRADING_DAYS)
            show_fig(charts.frontier_scatter(frontier, best, low, current=(m["Volatility"], ann_mu)))
            comp = pd.DataFrame({"Current": weights, "Max Sharpe": best[list(returns.columns)],
                                 "Min volatility": low[list(returns.columns)]}) * 100
            st.dataframe(comp.round(1))
            st.caption("Weights in %. Based on past returns only - this is an educational tool, not investment advice.")
