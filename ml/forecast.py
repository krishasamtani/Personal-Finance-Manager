"""Monthly expense forecasting with walk-forward model selection."""
import numpy as np
import pandas as pd


def _last(h):
    return float(h[-1])


def _ma3(h):
    return float(np.mean(h[-3:]))


def _trend(h):
    h = h[-6:]
    if len(h) < 3:
        return float(np.mean(h))
    slope, intercept = np.polyfit(np.arange(len(h)), h, 1)
    return max(0.0, float(intercept + slope * len(h)))


METHODS = {"Last month": _last, "3-month average": _ma3, "Linear trend (6m)": _trend}


def backtest(values, min_train=3):
    """Walk-forward one-step-ahead errors for each method."""
    errs = {k: [] for k in METHODS}
    for t in range(min_train, len(values)):
        for name, fn in METHODS.items():
            errs[name].append(values[t] - fn(values[:t]))
    return errs


def forecast_expenses(monthly_expense, horizon=3, z=1.28):
    """monthly_expense: Series indexed by month-start Timestamp (complete months only).

    Returns (forecast DataFrame[Month, Forecast, Lower, Upper], chosen method name, backtest MAE DataFrame).
    The method with the lowest walk-forward MAE is used when >= 6 months exist.
    """
    values = [float(v) for v in monthly_expense.values]
    n = len(values)
    if n == 0:
        raise ValueError("No expense history")
    errs = backtest(values) if n >= 6 else {}
    if errs:
        mae = {k: float(np.mean(np.abs(v))) for k, v in errs.items()}
        best = min(mae, key=mae.get)
        sigma = float(np.std(errs[best]))
    else:
        mae, best = {}, "3-month average"
        sigma = float(np.std(values)) if n > 1 else 0.15 * values[0]
    fn, hist, preds = METHODS[best], values[:], []
    for _ in range(horizon):
        p = fn(hist)
        preds.append(p)
        hist.append(p)
    preds = np.array(preds)
    width = z * sigma * np.sqrt(np.arange(1, horizon + 1))
    months = pd.date_range(monthly_expense.index[-1] + pd.offsets.MonthBegin(1), periods=horizon, freq="MS")
    out = pd.DataFrame({"Month": months, "Forecast": preds, "Lower": np.maximum(0.0, preds - width),
                        "Upper": preds + width})
    mae_df = pd.DataFrame({"Method": list(mae), "MAE": list(mae.values())}).sort_values("MAE") if mae else \
        pd.DataFrame(columns=["Method", "MAE"])
    return out, best, mae_df
