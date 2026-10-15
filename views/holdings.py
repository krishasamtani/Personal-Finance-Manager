import pandas as pd
import streamlit as st

import config
from core import charts, database, portfolio, prices
from views._ui import money, show_fig


def render(user_id):
    st.title("📈 Portfolio")
    assets = database.get_assets(user_id)
    holdings = portfolio.build_holdings(assets)

    if not holdings.empty:
        s = portfolio.portfolio_summary(holdings)
        c1, c2, c3 = st.columns(3)
        c1.metric("Invested (INR)", money(s["invested"]))
        c2.metric("Current value (INR)", money(s["value"]))
        c3.metric("Unrealised P/L", money(s["pnl"]), f"{s['pnl_pct']:+.1f}%")
        if st.button("🔄 Refresh live prices"):
            _refresh(user_id, holdings)
            st.rerun()
        st.dataframe(
            holdings, hide_index=True,
            column_config={
                "Quantity": st.column_config.NumberColumn(format="%.4f"),
                "Avg_cost": st.column_config.NumberColumn("Avg cost", format="%.2f"),
                "Current_price": st.column_config.NumberColumn("Price", format="%.2f"),
                "FX": st.column_config.NumberColumn("FX to INR", format="%.2f"),
                "Invested_INR": st.column_config.NumberColumn("Invested ₹", format="%.0f"),
                "Value_INR": st.column_config.NumberColumn("Value ₹", format="%.0f"),
                "PnL_INR": st.column_config.NumberColumn("P/L ₹", format="%.0f"),
                "PnL_pct": st.column_config.NumberColumn("P/L %", format="%.1f%%"),
            })
        left, right = st.columns(2)
        with left:
            show_fig(charts.allocation_donut(holdings))
        with right:
            show_fig(charts.pnl_bar(holdings))
        st.caption("Foreign-currency assets are converted to INR with Yahoo Finance FX rates "
                   "(approximate fallbacks are used when offline).")
    else:
        st.info("No holdings yet. Add your first asset below.")

    tab_add, tab_sell, tab_realised, tab_lots = st.tabs(["➕ Buy / add", "💸 Sell", "✅ Realised trades", "🧾 Raw lots"])
    with tab_add:
        _add_tab(user_id)
    with tab_sell:
        _sell_tab(user_id, holdings)
    with tab_realised:
        trades = database.get_realized_trades(user_id)
        if trades.empty:
            st.info("No sales yet.")
        else:
            st.metric("Total realised P/L", money(trades["Realized_pnl_inr"].sum()))
            st.dataframe(trades, hide_index=True)
    with tab_lots:
        if assets.empty:
            st.info("No lots.")
        else:
            st.dataframe(assets, hide_index=True)
            lot = st.selectbox("Delete a mistaken lot (ID)", assets["Asset_id"].tolist())
            if st.button("Delete lot"):
                database.delete_asset(user_id, lot)
                st.rerun()


def _refresh(user_id, holdings):
    ok, skipped, failed = [], [], []
    for r in holdings.itertuples():
        price, ccy = prices.fetch_quote(r.Asset_name)
        if price is None:
            failed.append(r.Asset_name)
        elif ccy and ccy != r.Currency:
            skipped.append(f"{r.Asset_name} (Yahoo quotes in {ccy}, stored as {r.Currency})")
        else:
            database.update_asset_price(user_id, r.Asset_name, price)
            ok.append(r.Asset_name)
    if ok:
        st.toast(f"Updated {', '.join(ok)}")
    if skipped:
        st.warning("Skipped (currency mismatch - re-add with the right currency): " + "; ".join(skipped))
    if failed:
        st.warning("No price found for: " + ", ".join(failed))


def _add_tab(user_id):
    ticker = st.text_input("Ticker (Yahoo Finance symbol, e.g. TCS.NS, AAPL, BTC-USD)").strip().upper()
    if st.button("Fetch price & currency") and ticker:
        price, ccy = prices.fetch_quote(ticker)
        if price is None:
            st.error("Couldn't fetch that ticker - enter the price manually.")
        st.session_state["fetched"] = {"ticker": ticker, "price": price or 0.0, "ccy": ccy or "INR"}
    fetched = st.session_state.get("fetched", {})
    if fetched.get("ticker") != ticker:
        fetched = {}
    ccy_default = fetched.get("ccy", "INR")
    ccy_options = config.SUPPORTED_CURRENCIES if ccy_default in config.SUPPORTED_CURRENCIES \
        else config.SUPPORTED_CURRENCIES + [ccy_default]
    with st.form("asset_form", clear_on_submit=True):
        qty = st.number_input("Quantity", min_value=0.0, format="%.6f")
        currency = st.selectbox("Asset currency", ccy_options, index=ccy_options.index(ccy_default))
        buy = st.number_input("Purchase price per unit (in the asset's currency)", min_value=0.0)
        cur = st.number_input("Current price per unit", min_value=0.0, value=float(fetched.get("price", 0.0)))
        if st.form_submit_button("Add to portfolio"):
            if not ticker or qty <= 0 or buy <= 0:
                st.error("Ticker, quantity and purchase price are required.")
            else:
                database.add_asset(user_id, ticker, qty, buy, cur or buy, currency)
                st.success(f"Added {qty:g} x {ticker}.")


def _sell_tab(user_id, holdings):
    if holdings.empty:
        st.info("Nothing to sell yet.")
        return
    ticker = st.selectbox("Asset", holdings["Asset_name"].tolist())
    row = holdings[holdings["Asset_name"] == ticker].iloc[0]
    qty = st.number_input(f"Quantity to sell (you hold {row['Quantity']:g})", min_value=0.0,
                          max_value=float(row["Quantity"]), format="%.6f")
    price = st.number_input(f"Sell price per unit ({row['Currency']})", min_value=0.0,
                            value=float(row["Current_price"]))
    if st.button("Sell (FIFO)"):
        if qty <= 0 or price <= 0:
            st.error("Enter a quantity and a sell price.")
        else:
            try:
                pnl = database.sell_asset(user_id, ticker, qty, price, prices.get_fx_rate(row["Currency"]))
                st.success(f"Sold {qty:g} x {ticker}. Realised P/L: {money(pnl)}")
                st.rerun()
            except ValueError as e:
                st.error(str(e))
