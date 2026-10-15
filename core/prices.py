"""Live prices, price history and FX rates from Yahoo Finance (yfinance imported lazily)."""
import time

import pandas as pd

FALLBACK_FX = {"INR": 1.0, "USD": 88.0, "EUR": 102.0, "GBP": 118.0}  # approximate, used offline
_FX_CACHE = {}  # currency -> (rate, timestamp, is_live)


def _yf():
    import yfinance as yf
    return yf


def _field(info, *keys):
    for k in keys:
        try:
            v = info[k]
            if v is not None:
                return v
        except Exception:
            continue
    return None


def fetch_quote(ticker):
    """Returns (price, currency); either can be None if Yahoo has no data."""
    try:
        t = _yf().Ticker(ticker)
        info = t.fast_info
        price, currency = _field(info, "last_price", "lastPrice"), _field(info, "currency")
        if price is None:
            hist = t.history(period="5d")
            if not hist.empty:
                price = hist["Close"].iloc[-1]
        return (float(price) if price is not None else None), currency
    except Exception:
        return None, None


def fetch_history(ticker, period="1y"):
    """DataFrame with columns Date (YYYY-MM-DD) and Close; empty if unavailable."""
    try:
        hist = _yf().Ticker(ticker).history(period=period, auto_adjust=True)
        if hist.empty:
            return pd.DataFrame(columns=["Date", "Close"])
        idx = hist.index
        if getattr(idx, "tz", None) is not None:
            idx = idx.tz_localize(None)
        return pd.DataFrame({"Date": idx.strftime("%Y-%m-%d"), "Close": hist["Close"].astype(float).values})
    except Exception:
        return pd.DataFrame(columns=["Date", "Close"])


def get_fx_rate(currency, base="INR"):
    """1 unit of `currency` in `base`. Cached for an hour; falls back to approximations offline."""
    if currency == base:
        return 1.0
    cached = _FX_CACHE.get(currency)
    now = time.time()
    if cached and now - cached[1] < (3600 if cached[2] else 300):
        return cached[0]
    price, _ = fetch_quote(f"{currency}{base}=X")
    if price:
        _FX_CACHE[currency] = (price, now, True)
        return price
    rate = FALLBACK_FX.get(currency, 1.0)
    _FX_CACHE[currency] = (rate, now, False)
    return rate
