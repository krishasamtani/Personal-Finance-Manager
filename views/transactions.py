import datetime as dt

import pandas as pd
import streamlit as st

import config
from core import analytics, database, importer
from ml import categorizer
from ml.dataset import generate_dataset

LOW_CONFIDENCE = 0.6


def render(user_id):
    st.title("✍️ Transactions")
    tab_add, tab_browse, tab_import = st.tabs(["➕ Add", "🔎 Browse & edit", "📥 Import bank CSV (ML)"])
    with tab_add:
        _add_tab(user_id)
    with tab_browse:
        _browse_tab(user_id)
    with tab_import:
        _import_tab(user_id)


def _add_tab(user_id):
    model = categorizer.get_model(user_id)
    desc = st.text_input("Description", placeholder="e.g. Swiggy order, Uber ride, Netflix", key="txn_desc")
    suggestion = None
    if desc.strip():
        pred = model.predict([desc]).iloc[0]
        suggestion = pred["Category"]
        st.caption(f"🤖 Suggested category: **{suggestion}** ({pred['Confidence']:.0%} confident)")
    cats = config.ALL_CATEGORIES
    default_idx = cats.index(suggestion) if suggestion in cats else cats.index("Other")
    with st.form("txn_form", clear_on_submit=True):
        date_ = st.date_input("Date", dt.date.today())
        category = st.selectbox("Category (income vs expense is derived from it)", cats, index=default_idx)
        amount = st.number_input(f"Amount ({config.CURRENCY_SYMBOL})", min_value=0.0, step=100.0)
        if st.form_submit_button("Save transaction"):
            if amount <= 0:
                st.error("Amount must be greater than 0.")
            else:
                source = "corrected" if suggestion and category != suggestion else "manual"
                database.add_transaction(user_id, date_, category, amount, config.category_type(category),
                                         desc, source)
                st.success("Saved.")


def _browse_tab(user_id):
    df = analytics.fetch_transactions(user_id)
    if df.empty:
        st.info("No transactions yet.")
        return
    f1, f2, f3, f4 = st.columns(4)
    with f1:
        dr = st.date_input("Date range", (df["Date"].min().date(), df["Date"].max().date()))
    with f2:
        tfilter = st.selectbox("Type", ["All", "Income", "Expense"])
    with f3:
        cats = st.multiselect("Category", sorted(df["Category"].unique()))
    with f4:
        query = st.text_input("Search description")
    start, end = (dr[0], dr[-1]) if isinstance(dr, (tuple, list)) and len(dr) else (dr, dr)
    view = df[(df["Date"].dt.date >= start) & (df["Date"].dt.date <= end)]
    if tfilter != "All":
        view = view[view["Type"] == tfilter]
    if cats:
        view = view[view["Category"].isin(cats)]
    if query:
        view = view[view["Description"].str.contains(query, case=False, na=False)]
    st.caption(f"{len(view)} transactions")

    edit = view[["Transaction_id", "Date", "Category", "Amount", "Description"]].copy()
    edit["Date"] = edit["Date"].dt.date
    edit["Delete"] = False
    key = f"txn_editor_{hash((str(start), str(end), tfilter, tuple(cats), query, len(df)))}"
    edited = st.data_editor(
        edit, hide_index=True, key=key,
        column_config={
            "Transaction_id": st.column_config.NumberColumn("ID", disabled=True),
            "Date": st.column_config.DateColumn("Date"),
            "Category": st.column_config.SelectboxColumn("Category", options=config.ALL_CATEGORIES, required=True),
            "Amount": st.column_config.NumberColumn("Amount", min_value=0.0, format="%.2f"),
            "Delete": st.column_config.CheckboxColumn("Delete?"),
        })
    b1, b2 = st.columns([1, 1])
    with b1:
        if st.button("Apply changes"):
            updated, deleted = _apply_edits(user_id, edit, edited)
            st.success(f"Updated {updated}, deleted {deleted}.")
            st.rerun()
    with b2:
        st.download_button("⬇️ Export filtered CSV", view.drop(columns=["Source"]).to_csv(index=False),
                           "transactions.csv", "text/csv")


def _apply_edits(user_id, original, edited):
    orig = original.set_index("Transaction_id")
    to_delete, updated = [], 0
    for _, r in edited.iterrows():
        tid = int(r["Transaction_id"])
        if r["Delete"]:
            to_delete.append(tid)
            continue
        o = orig.loc[tid]
        desc = "" if pd.isna(r["Description"]) else str(r["Description"])
        changes = {}
        if r["Category"] != o["Category"]:
            changes.update(Category=r["Category"], Type=config.category_type(r["Category"]), Source="corrected")
        if abs(float(r["Amount"]) - float(o["Amount"])) > 1e-9:
            changes["Amount"] = float(r["Amount"])
        if str(r["Date"])[:10] != str(o["Date"])[:10]:
            changes["Date"] = str(r["Date"])[:10]
        if desc != o["Description"]:
            changes["Description"] = desc
        if changes:
            database.update_transaction(user_id, tid, **changes)
            updated += 1
    if to_delete:
        database.delete_transactions(user_id, to_delete)
    return updated, len(to_delete)


def _import_tab(user_id):
    st.markdown("Upload a bank/UPI statement CSV with **Date**, **Description** and either **Amount** "
                "(negative = expense) or **Debit/Credit** columns. The model suggests a category for every "
                "row - fix the ones it got wrong and your corrections are used to retrain it.")
    sample = generate_dataset(3, seed=1).head(15)[["description"]].rename(columns={"description": "Description"})
    sample.insert(0, "Date", pd.date_range(end=pd.Timestamp.today().normalize(), periods=len(sample)).strftime("%Y-%m-%d"))
    sample["Amount"] = [-250, -120, -999, 80000, -450, -60, -1800, -649, -310, -2200, -75, -540, -399, -15000, -899]
    st.download_button("Download a sample statement", sample.to_csv(index=False), "sample_statement.csv", "text/csv")
    upload = st.file_uploader("Statement CSV", type="csv")
    if upload is None:
        return
    try:
        parsed = importer.normalize_statement(pd.read_csv(upload))
    except Exception as e:  # unreadable file or missing columns
        st.error(f"Couldn't read that file: {e}")
        return
    parsed = importer.drop_existing(parsed, analytics.fetch_transactions(user_id)).reset_index(drop=True)
    if parsed.empty:
        st.info("Nothing new to import (all rows already exist or the file is empty).")
        return
    pred = categorizer.get_model(user_id).predict(parsed["Description"].tolist(), types=parsed["Type"].tolist())
    preview = parsed.copy()
    preview["Category"] = pred["Category"].values
    preview["Confidence"] = (pred["Confidence"].values * 100).round()
    preview["Date"] = preview["Date"].dt.date
    preview.insert(0, "Import", True)
    needs_review = int((pred["Confidence"] < LOW_CONFIDENCE).sum())
    m1, m2 = st.columns(2)
    m1.metric("New rows", len(preview))
    m2.metric("Low-confidence rows", needs_review, help=f"Confidence below {LOW_CONFIDENCE:.0%} - please review")
    edited = st.data_editor(
        preview, hide_index=True, key=f"import_{hash(upload.name)}_{len(preview)}",
        disabled=["Date", "Description", "Amount", "Type", "Confidence"],
        column_config={
            "Category": st.column_config.SelectboxColumn("Category", options=config.ALL_CATEGORIES, required=True),
            "Confidence": st.column_config.NumberColumn("Confidence", format="%d%%"),
        })
    if st.button("Import selected rows"):
        chosen = edited[edited["Import"]]
        rows = []
        for idx, r in chosen.iterrows():
            changed = r["Category"] != pred.loc[idx, "Category"]
            rows.append({"Date": r["Date"], "Category": r["Category"], "Amount": r["Amount"],
                         "Type": config.category_type(r["Category"]), "Description": r["Description"],
                         "Source": "corrected" if changed else "imported"})
        n = database.add_transactions_bulk(user_id, rows)
        st.success(f"Imported {n} transactions. Open the ML Lab and retrain to learn from your corrections.")
