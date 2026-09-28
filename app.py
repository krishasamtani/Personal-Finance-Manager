import streamlit as st
import datetime
from analytics import get_financial_summary, fetch_transactions, fetch_portfolio_assets, get_spending_by_category
from database import add_transaction, add_portfolio_asset, add_user, get_all_users, update_asset_price, delete_user
from visualizer import plot_spending_chart, plot_portfolio_allocation, plot_portfolio_profit_loss, plot_income_vs_expense_chart
from price_fetcher import fetch_live_price, fetch_live_prices

# Page Config
st.set_page_config(page_title="Advanced Finance & Portfolio Tracker", page_icon="📈", layout="wide")

# --- SIDEBAR: USER MANAGEMENT & NAVIGATION ---
st.sidebar.title("👤 User Profile")

users = get_all_users()
user_dict = {name: uid for uid, name in users}
selected_user_name = st.sidebar.selectbox("Select Active User", list(user_dict.keys()))
active_user_id = user_dict[selected_user_name]

# Naya user add karne ka option
with st.sidebar.expander("➕ Add New User"):
    new_user_name = st.text_input("User Name")
    if st.button("Create User"):
        if new_user_name.strip() != "":
            add_user(new_user_name)
            st.success(f"User '{new_user_name}' created!")
            st.rerun()

# User delete karne ka option
with st.sidebar.expander("🗑️ Delete User"):
    if len(user_dict) <= 1:
        st.info("At least one user must remain — add another user before deleting this one.")
    else:
        user_to_delete = st.selectbox("Select user to delete", list(user_dict.keys()), key="delete_user_select")
        st.warning(f"⚠️ This will permanently delete '{user_to_delete}' and ALL their transactions and portfolio assets. This cannot be undone.")
        confirm_delete = st.checkbox(f"Yes, I'm sure I want to delete '{user_to_delete}'", key="confirm_delete_checkbox")
        if st.button("Delete User Permanently", disabled=not confirm_delete):
            delete_user(user_dict[user_to_delete])
            st.success(f"User '{user_to_delete}' and all their data have been deleted.")
            st.rerun()

st.sidebar.markdown("---")
st.sidebar.title("🧭 Navigation")
page = st.sidebar.radio("Go to", ["📊 Dashboard & Analytics", "✍️ Add Transactions & Assets"])

# --- PAGE 1: DASHBOARD ---
if page == "📊 Dashboard & Analytics":
    st.title(f"💰 Personal Finance Dashboard — Welcome, {selected_user_name}!")
    st.markdown("---")

    # Fetch Summary Data for Active User
    summary = get_financial_summary(user_id=active_user_id)

    # Top Metric Cards
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric(label="Total Income", value=f"₹ {summary['Total Income']:,.2f}")
    with col2:
        st.metric(label="Total Expense", value=f"₹ {summary['Total Expense']:,.2f}")
    with col3:
        st.metric(label="Net Savings", value=f"₹ {summary['Net Savings']:,.2f}")
    with col4:
        st.metric(label="Portfolio Profit/Loss", value=f"₹ {summary['Total Profit/Loss']:,.2f}", 
                  delta=f"{summary['Profit/Loss Percentage']:.2f}%")

    st.markdown("---")

    # General Financial Insights (Charts 1 & 2)
    st.subheader("📊 General Financial Insights")
    gen_col1, gen_col2 = st.columns(2)

    with gen_col1:
        st.markdown("### Expense Breakdown by Category")
        spending_data = get_spending_by_category(user_id=active_user_id)
        fig1 = plot_spending_chart(spending_data)
        st.pyplot(fig1)

    with gen_col2:
        st.markdown("### Income vs Expense Comparison")
        fig2 = plot_income_vs_expense_chart(summary['Total Income'], summary['Total Expense'])
        st.pyplot(fig2)

    st.markdown("---")

    # Investment Portfolio Performance (Charts 3 & 4)
    header_col1, header_col2 = st.columns([4, 1])
    with header_col1:
        st.subheader("📈 Investment Portfolio Performance")
    with header_col2:
        refresh_clicked = st.button("🔄 Refresh Live Prices", use_container_width=True)

    portfolio_df = fetch_portfolio_assets(user_id=active_user_id)

    if refresh_clicked:
        if portfolio_df.empty:
            st.info("No assets to refresh yet — add one below first.")
        else:
            with st.spinner("Fetching live prices..."):
                tickers = portfolio_df['Asset_name'].tolist()
                live_prices = fetch_live_prices(tickers)

                updated, failed = [], []
                for _, row in portfolio_df.iterrows():
                    price = live_prices.get(row['Asset_name'])
                    if price is not None:
                        update_asset_price(row['Asset_id'], price)
                        updated.append(row['Asset_name'])
                    else:
                        failed.append(row['Asset_name'])

            if updated:
                st.success(f"✅ Updated live prices for: {', '.join(updated)}")
            if failed:
                st.warning(f"⚠️ Couldn't fetch prices for: {', '.join(failed)} — check the ticker symbol (e.g. use 'BTC-USD' for crypto, not just 'BTC').")

            portfolio_df = fetch_portfolio_assets(user_id=active_user_id)

    port_col1, port_col2 = st.columns(2)

    with port_col1:
        st.markdown("### Portfolio Asset Allocation")
        fig3 = plot_portfolio_allocation(portfolio_df)
        st.pyplot(fig3)

    with port_col2:
        st.markdown("### Asset-wise Profit & Loss")
        fig4 = plot_portfolio_profit_loss(portfolio_df)
        st.pyplot(fig4)

    st.markdown("---")

    # Detailed Data Tables
    st.subheader("📋 Relational Database Records")
    tab1, tab2 = st.tabs(["Transactions Table", "Portfolio Assets Table"])
    with tab1:
        st.dataframe(fetch_transactions(user_id=active_user_id), use_container_width=True)
    with tab2:
        st.dataframe(fetch_portfolio_assets(user_id=active_user_id), use_container_width=True)

# --- PAGE 2: USER INPUT FORMS ---
elif page == "✍️ Add Transactions & Assets":
    st.title(f"✍️ Input Financial Data for {selected_user_name}")
    st.markdown("You can add new transactions and portfolio assets to the live database.")
    st.markdown("---")

    col_form1, col_form2 = st.columns(2)

    with col_form1:
        st.subheader("➕ Add New Transaction")
        with st.form("transaction_form"):
            trans_date = st.date_input("Date", datetime.date.today())
            trans_type = st.selectbox("Type", ["Income", "Expense"])
            category = st.selectbox("Category", ["Food", "Rent", "Salary", "Utilities", "Entertainment", "Investment", "Other"])
            amount = st.number_input("Amount (₹)", min_value=0.0, step=100.0)
            
            submit_trans = st.form_submit_button("Save Transaction")
            if submit_trans:
                add_transaction(str(trans_date), category, amount, trans_type, user_id=active_user_id)
                st.success("🎉 Transaction successfully added to database!")

    with col_form2:
        st.subheader("📈 Add New Portfolio Asset")

        # Outside the form, so we can fetch live price on button click
        # before the user submits (st.form only runs code on submit).
        fetch_col1, fetch_col2 = st.columns([3, 1])
        with fetch_col1:
            ticker_input = st.text_input("Asset Ticker (e.g., AAPL, TSLA, BTC-USD)", key="ticker_input")
        with fetch_col2:
            st.write("")  # spacing to align button with text input
            fetch_price_clicked = st.button("🔍 Fetch Price")

        if fetch_price_clicked:
            if ticker_input.strip() == "":
                st.warning("Enter a ticker symbol first.")
            else:
                with st.spinner(f"Fetching live price for {ticker_input}..."):
                    live_price = fetch_live_price(ticker_input.strip())
                if live_price is not None:
                    st.session_state["fetched_price"] = live_price
                    st.session_state["fetched_ticker"] = ticker_input.strip()
                    st.success(f"✅ {ticker_input.strip()} current price: ₹{live_price:,.2f}")
                else:
                    st.session_state.pop("fetched_price", None)
                    st.error(f"Couldn't fetch price for '{ticker_input}'. Check the ticker symbol (e.g. use 'BTC-USD' for crypto, not just 'BTC').")

        st.caption("Use the exact ticker symbol Yahoo Finance recognizes — e.g. 'BTC-USD' for Bitcoin, not just 'BTC'.")

        # Pre-fill current price if we fetched one for this exact ticker
        default_current_price = 0.0
        if st.session_state.get("fetched_ticker") == ticker_input.strip() and "fetched_price" in st.session_state:
            default_current_price = st.session_state["fetched_price"]

        with st.form("portfolio_form"):
            st.text_input("Asset Ticker (confirm)", value=ticker_input, disabled=True)
            quantity = st.number_input("Quantity", min_value=0.0, step=1.0)
            purchase_price = st.number_input("Purchase Price per unit (₹)", min_value=0.0, step=10.0)
            current_price = st.number_input(
                "Current Market Price per unit (₹)",
                min_value=0.0, step=10.0,
                value=float(default_current_price),
                help="Auto-filled from 'Fetch Price' above — you can still adjust it manually if needed."
            )
            asset_name = ticker_input
            
            submit_port = st.form_submit_button("Save Asset")
            if submit_port:
                if asset_name.strip() != "":
                    add_portfolio_asset(asset_name, quantity, purchase_price, current_price, user_id=active_user_id)
                    st.success("🎉 Portfolio asset successfully added to database!")
                else:
                    st.error("Kindly enter the name of an asset!")