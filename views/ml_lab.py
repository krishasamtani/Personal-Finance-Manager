import streamlit as st

from core import charts, database
from ml import categorizer
from views._ui import show_fig


def render(user_id):
    st.title("🧪 ML Lab - Expense Categoriser")
    with st.expander("How it works", expanded=False):
        st.markdown(
            "- **Features:** TF-IDF on words *and* character n-grams (robust to typos and bank noise like "
            "`UPI/SWIGGY/4821@okhdfc`).\n"
            "- **Model:** linear classifier (logistic regression by default; SVM and Naive Bayes compared below).\n"
            "- **Training data:** synthetic statement text to bootstrap, plus *your* labelled transactions "
            "(weighted 5x) so it adapts to the merchants you actually use.\n"
            "- **Evaluation:** a random split looks perfect because the same merchants appear in train and test "
            "(leakage). Holding out whole merchants measures what really matters: unseen merchants.")
    model = categorizer.get_model(user_id)
    tab_try, tab_eval, tab_train = st.tabs(["Try it", "Evaluation", "Personalise"])

    with tab_try:
        text = st.text_area("Descriptions (one per line)",
                            "UPI/ZOMATO/88123@okaxis\nMonthly salary credit\nApollo Pharmacy Pune\nsome random shop")
        lines = [l for l in text.splitlines() if l.strip()]
        if lines:
            proba = model.predict_proba(lines)
            top = proba.apply(lambda r: ", ".join(f"{c} {p:.0%}" for c, p in r.nlargest(3).items()), axis=1)
            out = model.predict(lines)
            out.insert(0, "Description", lines)
            out["Confidence"] = (out["Confidence"] * 100).round()
            out["Top 3"] = top.values
            st.dataframe(out, hide_index=True,
                         column_config={"Confidence": st.column_config.NumberColumn(format="%d%%")})

    with tab_eval:
        st.write("5-fold cross-validation, macro-averaged F1 (each category counts equally).")
        if st.button("Run evaluation (about 10 seconds)"):
            with st.spinner("Training and evaluating..."):
                st.session_state["ml_eval"] = (categorizer.evaluate_models(), categorizer.detailed_report())
        if "ml_eval" in st.session_state:
            results, (labels, cm, report) = st.session_state["ml_eval"]
            st.dataframe(results.round(3), hide_index=True)
            show_fig(charts.model_comparison_bar(results))
            st.caption("The gap between the two bars is data leakage: models memorise merchant names. "
                       "That is why personalising with your own data matters.")
            show_fig(charts.confusion_matrix_fig(cm, labels))
            st.dataframe(report.round(2))

    with tab_train:
        labelled = database.get_labelled_descriptions(user_id)
        st.metric("Your labelled transactions", len(labelled))
        st.write("Transactions you add or correct by hand are used as training data. "
                 "Retrain after importing and fixing a statement.")
        if st.button("Retrain on my data"):
            with st.spinner("Retraining..."):
                n = categorizer.retrain(user_id)
            st.success(f"Model retrained with {n} of your own examples.")
