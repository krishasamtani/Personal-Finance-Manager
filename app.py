"""FinTrack - personal finance & portfolio tracker with ML (Streamlit)."""
import streamlit as st

from core import auth, database, demo
from views import budgets, dashboard, holdings, insights, ml_lab, risk, transactions

st.set_page_config(page_title="FinTrack", page_icon="💰", layout="wide")
database.init_db()

PAGES = {
    "📊 Dashboard": dashboard.render,
    "✍️ Transactions": transactions.render,
    "📈 Portfolio": holdings.render,
    "🛡️ Portfolio Risk": risk.render,
    "🎯 Budgets": budgets.render,
    "🤖 AI Insights": insights.render,
    "🧪 ML Lab": ml_lab.render,
}


def login_screen():
    st.title("💰 FinTrack")
    st.caption("Personal finance & portfolio tracker with ML-powered expense categorisation")
    tab_login, tab_signup = st.tabs(["Log in", "Sign up"])
    with tab_login:
        with st.form("login_form"):
            name = st.text_input("Username")
            password = st.text_input("Password", type="password")
            if st.form_submit_button("Log in"):
                uid, msg = auth.login(name, password)
                if uid:
                    st.session_state["user_id"] = uid
                    st.session_state["user_name"] = database.get_user(uid)["Name"]
                    st.rerun()
                else:
                    st.error(msg)
        st.caption("Existing account from the old version? Log in with your name and choose a password.")
    with tab_signup:
        with st.form("signup_form"):
            name = st.text_input("Choose a username")
            password = st.text_input("Choose a password (6+ characters)", type="password")
            if st.form_submit_button("Create account"):
                uid, msg = auth.register(name, password)
                if uid:
                    st.session_state["user_id"] = uid
                    st.session_state["user_name"] = name.strip()
                    st.rerun()
                else:
                    st.error(msg)


def sidebar(user_id):
    with st.sidebar:
        st.markdown(f"### 👤 {st.session_state['user_name']}")
        if st.button("Log out"):
            st.session_state.clear()
            st.rerun()
        page = st.radio("Navigate", list(PAGES), label_visibility="collapsed")
        st.divider()
        if st.button("✨ Load demo data"):
            n = demo.load_demo_data(user_id)
            st.success(f"Loaded {n} demo transactions, 5 holdings and budgets.")
    return page


if "user_id" not in st.session_state:
    login_screen()
else:
    uid = st.session_state["user_id"]
    PAGES[sidebar(uid)](uid)