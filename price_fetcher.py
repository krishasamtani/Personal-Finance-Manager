import yfinance as yf

def fetch_live_price(ticker):
    """
    Fetch the latest market price for a given ticker symbol using yfinance.
    Works for stocks (AAPL, TSLA), indices, and crypto (BTC-USD, ETH-USD).

    Returns the price as a float, or None if it couldn't be fetched
    (e.g. invalid ticker, network issue, or delisted symbol).
    """
    try:
        stock = yf.Ticker(ticker)
        # fast_info is quicker than .info and avoids pulling unnecessary data
        price = stock.fast_info.get("last_price")

        if price is None:
            # Fallback: grab the most recent closing price from history
            hist = stock.history(period="1d")
            if not hist.empty:
                price = hist["Close"].iloc[-1]

        return float(price) if price is not None else None
    except Exception:
        return None


def fetch_live_prices(tickers):
    """
    Fetch live prices for a list of ticker symbols in one go.
    Returns a dict: {ticker: price_or_None}
    """
    results = {}
    for ticker in tickers:
        results[ticker] = fetch_live_price(ticker)
    return results