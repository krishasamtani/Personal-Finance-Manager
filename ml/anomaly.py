"""Flag unusually large expenses (Isolation Forest, with a robust z-score fallback for small data)."""
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

MIN_FOR_FOREST = 30
MIN_MULTIPLE = 1.5  # an anomaly must also be >= 1.5x the typical amount of its category


def detect_anomalies(df, contamination=0.04, seed=42):
    """Returns the expense rows with extra columns Anomaly (bool), Score (higher = stranger), Reason."""
    exp = df[df["Type"] == "Expense"].copy()
    if exp.empty:
        return exp.assign(Anomaly=False, Score=0.0, Reason="")
    med = exp.groupby("Category")["Amount"].transform("median")
    exp["Multiple"] = exp["Amount"] / med.where(med > 0, np.nan)
    exp["Multiple"] = exp["Multiple"].fillna(1.0)
    log_amt = np.log1p(exp["Amount"])
    rel = np.log((exp["Amount"] + 1) / (med + 1))
    if len(exp) >= MIN_FOR_FOREST:
        X = np.column_stack([log_amt, rel])
        forest = IsolationForest(n_estimators=200, contamination=contamination, random_state=seed).fit(X)
        exp["Score"] = -forest.score_samples(X)
        outlier = forest.predict(X) == -1
    else:
        mad = (log_amt - log_amt.groupby(exp["Category"]).transform("median")).abs() \
            .groupby(exp["Category"]).transform("median")
        z = 0.6745 * (log_amt - log_amt.groupby(exp["Category"]).transform("median")) / mad.replace(0, np.nan)
        exp["Score"] = z.fillna(0.0)
        outlier = (exp["Score"] > 3.5).to_numpy()
    exp["Anomaly"] = outlier & (exp["Multiple"] >= MIN_MULTIPLE).to_numpy()
    exp["Reason"] = np.where(exp["Anomaly"], exp["Multiple"].round(1).astype(str) + "x typical " + exp["Category"], "")
    return exp.sort_values("Score", ascending=False)
