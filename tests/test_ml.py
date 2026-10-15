import numpy as np
import pandas as pd
import pytest

from core import database
from ml import anomaly, categorizer, forecast
from tests.helpers import fresh_env


def test_categorizer_known_merchants():
    m = categorizer.train_model()
    pred = m.predict(["SWIGGY ORDER 8891", "Netflix subscription", "UPI/OLA/4821@ybl", "monthly salary credit"])
    assert list(pred["Category"]) == ["Food", "Entertainment", "Transport", "Salary"]
    assert (pred["Confidence"] > 0.5).all()


def test_type_restriction_and_low_confidence():
    m = categorizer.train_model()
    assert m.predict(["Amazon"], types=["Income"]).loc[0, "Category"] in ("Refund", "Salary", "Freelance", "Interest")
    assert m.predict(["qwxzv plmk"]).loc[0, "Confidence"] < 0.5


def test_personalisation_learns_user_labels():
    fresh_env()
    u = database.create_user("a")
    for i in range(6):
        database.add_transaction(u, "2026-01-0%d" % (i + 1), "Health", 100, "Expense", "Dr Sharma Ortho Clinic", "manual")
    categorizer.retrain(u)
    assert categorizer.get_model(u).predict(["Dr Sharma Ortho Clinic"]).loc[0, "Category"] == "Health"


def test_unseen_merchant_evaluation_is_harder_than_random_split():
    r = categorizer.evaluate_models(n_per_class=60, kinds=("logreg",)).iloc[0]
    assert r["Random split F1"] > 0.9
    assert 0.2 < r["Unseen-merchant F1"] < r["Random split F1"]


def test_forecast_picks_trend_and_handles_short_history():
    s = pd.Series([30000, 32000, 31000, 35000, 36000, 38000, 37000, 40000], index=pd.date_range("2026-01-01", periods=8, freq="MS"))
    fc, method, mae = forecast.forecast_expenses(s, horizon=3)
    assert len(fc) == 3 and fc["Forecast"].iloc[0] > 38000 and (fc["Lower"] <= fc["Forecast"]).all()
    assert fc["Month"].iloc[0] == pd.Timestamp("2026-09-01") and not mae.empty
    fc2, method2, mae2 = forecast.forecast_expenses(s.iloc[:3])
    assert method2 == "3-month average" and mae2.empty


def test_anomaly_detection_flags_outlier():
    rng = np.random.default_rng(0)
    df = pd.DataFrame({"Type": "Expense", "Category": rng.choice(["Food", "Shopping"], 60),
                       "Amount": rng.uniform(100, 600, 60), "Date": pd.date_range("2026-01-01", periods=60)})
    df.loc[5, ["Category", "Amount"]] = ["Shopping", 75000]
    flagged = anomaly.detect_anomalies(df)
    assert flagged[flagged["Anomaly"]].index.tolist() == [5] or 5 in flagged[flagged["Anomaly"]].index
