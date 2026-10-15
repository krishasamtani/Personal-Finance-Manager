import pandas as pd
import streamlit as st

from core import analytics, charts, database, portfolio
from views._ui import money, show_fig


def render(user_id):
    st.title("📊 Dashboard")
    tx = analytics.fetch_transactions(user_id)
    holdings = portfolio.build_holdings(database.get_assets(user_id))
    if tx.empty and holdings.empty:
        st.info("No data yet. Add transactions or holdings, or click **Load demo data** in the sidebar.")
        return

    s = analytics.financial_summary(tx, portfolio.portfolio_summary(holdings))
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total income", money(s["income"]))
    c2.metric("Total expenses", money(s["expense"]))
    c3.metric("Net savings", money(s["savings"]), f"{s['savings_rate']:.0f}% savings rate")
    c4.metric("Portfolio value", money(s["portfolio_value"]), f"{s['portfolio_pnl_pct']:+.1f}% unrealised")

    status = analytics.budget_status(tx, database.get_budgets(user_id))
    for r in status[status["Status"] == "Over"].itertuples():
        st.warning(f"Over budget on **{r.Category}**: {money(r.Spent)} spent of {money(r.Limit)} this month.")

    insights = analytics.generate_insights(tx)
    if insights:
        st.subheader("💡 Quick insights")
        for line in insights:
            st.markdown(f"- {line}")

    if not tx.empty:
        monthly = analytics.monthly_summary(tx)
        left, right = st.columns(2)
        with left:
            show_fig(charts.income_vs_expense(monthly))
        with right:
            show_fig(charts.savings_rate_line(monthly))

        months = sorted(tx["Date"].dt.to_period("M").unique(), reverse=True)
        chosen = st.selectbox("Spending breakdown for", months, format_func=lambda p: p.strftime("%B %Y"))
        spending = analytics.spending_by_category(tx, chosen)
        left, right = st.columns([3, 2])
        with left:
            show_fig(charts.spending_bar(spending))
        with right:
            st.dataframe(spending, hide_index=True)

        st.subheader("Recent transactions")
        recent = tx.sort_values("Date", ascending=False).head(10)
        st.dataframe(recent[["Date", "Category", "Type", "Amount", "Description"]], hide_index=True)
