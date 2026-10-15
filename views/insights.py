import pandas as pd
import streamlit as st

from core import analytics, charts
from ml import anomaly, forecast
from views._ui import money, show_fig


def render(user_id):
    st.title("🤖 AI Insights")
    tx = analytics.fetch_transactions(user_id)
    if tx.empty:
        st.info("Add transactions (or load demo data) to unlock forecasts and anomaly detection.")
        return

    result = anomaly.detect_anomalies(tx)
    flagged = result[result["Anomaly"]]

    st.subheader("📅 Expense forecast")
    # Forecast baseline spending: one-off purchases flagged as anomalies would otherwise distort the trend.
    baseline = tx.drop(index=flagged.index)
    expenses = analytics.monthly_summary(baseline).set_index("Month")["Expense"]
    current = pd.Timestamp.today().to_period("M").to_timestamp()
    history = expenses[expenses.index < current]  # drop the incomplete current month
    if len(history) < 3:
        st.info("Need at least 3 complete months of expenses to forecast.")
    else:
        fc, method, mae = forecast.forecast_expenses(history, horizon=3)
        show_fig(charts.forecast_chart(history, fc))
        st.markdown(f"Method used: **{method}**" +
                    (" (lowest walk-forward error)." if not mae.empty else " (too little history to compare methods)."))
        if len(flagged):
            st.caption(f"{len(flagged)} unusual one-off expense(s) were excluded so they don't skew the forecast.")
        shown = fc.copy()
        shown["Month"] = shown["Month"].dt.strftime("%b %Y")
        st.dataframe(shown.round(0), hide_index=True)
        if not mae.empty:
            with st.expander("Backtest: how accurate was each method?"):
                st.dataframe(mae.round(0), hide_index=True)
                st.caption("MAE = average one-month-ahead error in rupees, measured walk-forward on your own history.")

    st.subheader("🚨 Unusual expenses")
    if flagged.empty:
        st.success("No unusual expenses detected.")
    else:
        st.warning(f"{len(flagged)} expense(s) look unusually large for their category.")
        st.dataframe(flagged[["Date", "Category", "Amount", "Description", "Reason"]], hide_index=True)
    show_fig(charts.anomaly_scatter(result))
    st.caption("Isolation Forest on log-amount and amount relative to the category median "
               "(robust z-score when fewer than 30 expenses).")

    st.subheader("💡 Observations")
    for line in analytics.generate_insights(tx):
        st.markdown(f"- {line}")
