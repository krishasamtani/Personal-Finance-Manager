import pandas as pd
import streamlit as st

import config
from core import analytics, database
from views._ui import money


def render(user_id):
    st.title("🎯 Budgets")
    existing = database.get_budgets(user_id).set_index("Category")["Monthly_limit"].to_dict()
    table = pd.DataFrame({"Category": config.EXPENSE_CATEGORIES,
                          "Monthly_limit": [float(existing.get(c, 0.0)) for c in config.EXPENSE_CATEGORIES]})
    st.caption("Set a monthly limit per category (0 = no budget).")
    edited = st.data_editor(
        table, hide_index=True, disabled=["Category"], key="budget_editor",
        column_config={"Monthly_limit": st.column_config.NumberColumn("Monthly limit", min_value=0.0, step=500.0)})
    if st.button("Save budgets"):
        database.set_budgets(user_id, dict(zip(edited["Category"], edited["Monthly_limit"])))
        st.success("Budgets saved.")
        st.rerun()

    status = analytics.budget_status(analytics.fetch_transactions(user_id), database.get_budgets(user_id))
    st.subheader("This month")
    if status.empty:
        st.info("No budgets set yet.")
        return
    for r in status.itertuples():
        st.progress(min(r.Pct / 100, 1.0), text=f"{r.Category}: {money(r.Spent)} of {money(r.Limit)} ({r.Pct:.0f}%)")
        if r.Status == "Over":
            st.error(f"{r.Category} is over budget by {money(-r.Remaining)}.")
        elif r.Status == "Warning":
            st.warning(f"{r.Category} has used {r.Pct:.0f}% of its budget.")
