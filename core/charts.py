"""Matplotlib / seaborn figures. Every function returns a Figure (the UI layer displays and closes it)."""
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

import config

sns.set_theme(style="whitegrid", context="notebook")
SYM = config.CURRENCY_SYMBOL
GREEN, RED, BLUE, GREY = "#2ecc71", "#e74c3c", "#3498db", "#b0b0b0"


def _fig(w=7, h=4.2):
    return plt.subplots(figsize=(w, h))


def _empty(msg="No data yet"):
    fig, ax = _fig()
    ax.text(0.5, 0.5, msg, ha="center", va="center", fontsize=12, color="gray")
    ax.axis("off")
    return fig


def spending_bar(spending):
    if spending.empty:
        return _empty("No expenses in this period")
    fig, ax = _fig()
    sns.barplot(data=spending, x="Amount", y="Category", hue="Category", palette="viridis", legend=False, ax=ax)
    for c in ax.containers:
        ax.bar_label(c, fmt="%.0f", padding=2, fontsize=8)
    ax.set(xlabel=f"Amount ({SYM})", ylabel="", title="Spending by category")
    fig.tight_layout()
    return fig


def income_vs_expense(monthly):
    if monthly.empty:
        return _empty()
    m = monthly.melt(id_vars="Month", value_vars=["Income", "Expense"], var_name="Type", value_name="Amount")
    m["Label"] = m["Month"].dt.strftime("%b %y")
    fig, ax = _fig()
    sns.barplot(data=m, x="Label", y="Amount", hue="Type", palette={"Income": GREEN, "Expense": RED}, ax=ax)
    ax.set(xlabel="", ylabel=f"Amount ({SYM})", title="Income vs expense")
    plt.setp(ax.get_xticklabels(), rotation=45, ha="right")
    fig.tight_layout()
    return fig


def savings_rate_line(monthly):
    if monthly.empty:
        return _empty()
    fig, ax = _fig()
    ax.plot(monthly["Month"].dt.strftime("%b %y"), monthly["Savings_rate"], marker="o", color=BLUE)
    ax.axhline(20, ls="--", color=GREY, label="20% guideline")
    ax.set(ylabel="Savings rate (%)", title="Savings rate by month")
    ax.legend()
    plt.setp(ax.get_xticklabels(), rotation=45, ha="right")
    fig.tight_layout()
    return fig


def allocation_donut(holdings):
    if holdings.empty:
        return _empty("No holdings yet")
    fig, ax = _fig(5.5, 4.5)
    ax.pie(holdings["Value_INR"], labels=holdings["Asset_name"], autopct="%1.1f%%", startangle=140,
           colors=sns.color_palette("pastel", len(holdings)), wedgeprops=dict(width=0.45))
    ax.set_title("Allocation by current value")
    return fig


def pnl_bar(holdings):
    if holdings.empty:
        return _empty("No holdings yet")
    fig, ax = _fig(5.5, 4.5)
    colors = [GREEN if v >= 0 else RED for v in holdings["PnL_INR"]]
    ax.bar(holdings["Asset_name"], holdings["PnL_INR"], color=colors)
    ax.axhline(0, color="black", lw=0.8)
    ax.set(ylabel=f"Unrealised P/L ({SYM})", title="Profit / loss by asset")
    plt.setp(ax.get_xticklabels(), rotation=30, ha="right")
    fig.tight_layout()
    return fig


def cumulative_returns(returns, port):
    fig, ax = _fig(8, 4.5)
    (1 + returns).cumprod().plot(ax=ax, lw=1, alpha=0.7)
    (1 + port).cumprod().plot(ax=ax, lw=2.5, color="black", label="Portfolio")
    ax.set(ylabel="Growth of 1 unit", xlabel="", title="Cumulative performance")
    ax.legend(fontsize=8)
    fig.tight_layout()
    return fig


def drawdown_chart(port):
    wealth = (1 + port).cumprod()
    dd = wealth / wealth.cummax() - 1
    fig, ax = _fig(8, 3.2)
    ax.fill_between(dd.index, dd.values * 100, 0, color=RED, alpha=0.4)
    ax.set(ylabel="Drawdown (%)", title="Portfolio drawdown (underwater chart)")
    fig.tight_layout()
    return fig


def correlation_heatmap(returns):
    fig, ax = _fig(6, 4.8)
    sns.heatmap(returns.corr(), annot=True, fmt=".2f", cmap="coolwarm", vmin=-1, vmax=1, ax=ax)
    ax.set_title("Correlation of daily returns")
    fig.tight_layout()
    return fig


def frontier_scatter(frontier, best, min_vol, current=None):
    fig, ax = _fig(8, 4.8)
    sc = ax.scatter(frontier["Volatility"] * 100, frontier["Return"] * 100, c=frontier["Sharpe"],
                    cmap="viridis", s=8, alpha=0.6)
    fig.colorbar(sc, ax=ax, label="Sharpe ratio")
    ax.scatter(best["Volatility"] * 100, best["Return"] * 100, marker="*", s=250, color="gold",
               edgecolor="black", label="Max Sharpe", zorder=3)
    ax.scatter(min_vol["Volatility"] * 100, min_vol["Return"] * 100, marker="D", s=80, color="white",
               edgecolor="black", label="Min volatility", zorder=3)
    if current is not None:
        ax.scatter(current[0] * 100, current[1] * 100, marker="X", s=120, color=RED, label="Your portfolio", zorder=3)
    ax.set(xlabel="Volatility (% / yr)", ylabel="Expected return (% / yr)", title="Random portfolios & efficient frontier")
    ax.legend()
    fig.tight_layout()
    return fig


def forecast_chart(history, fc):
    fig, ax = _fig(8, 4)
    ax.plot(history.index, history.values, marker="o", color=BLUE, label="Actual")
    ax.plot(fc["Month"], fc["Forecast"], marker="o", ls="--", color=RED, label="Forecast")
    ax.fill_between(fc["Month"], fc["Lower"], fc["Upper"], color=RED, alpha=0.15, label="80% interval")
    ax.set(ylabel=f"Expenses ({SYM})", title="Monthly expense forecast")
    ax.legend()
    fig.tight_layout()
    return fig


def anomaly_scatter(exp):
    if exp.empty:
        return _empty("No expenses yet")
    fig, ax = _fig(8, 4)
    normal, odd = exp[~exp["Anomaly"]], exp[exp["Anomaly"]]
    ax.scatter(normal["Date"], normal["Amount"], s=14, color=GREY, label="Normal")
    ax.scatter(odd["Date"], odd["Amount"], s=60, color=RED, label="Unusual", zorder=3)
    ax.set_yscale("log")
    ax.set(ylabel=f"Amount ({SYM}, log scale)", title="Expenses and detected anomalies")
    ax.legend()
    fig.tight_layout()
    return fig


def confusion_matrix_fig(cm, labels):
    fig, ax = _fig(8.5, 6.5)
    sns.heatmap(cm, annot=True, fmt="d", cmap="Blues", xticklabels=labels, yticklabels=labels, cbar=False, ax=ax)
    ax.set(xlabel="Predicted", ylabel="Actual", title="Confusion matrix on unseen merchants")
    plt.setp(ax.get_xticklabels(), rotation=45, ha="right")
    fig.tight_layout()
    return fig


def model_comparison_bar(results):
    m = results.melt(id_vars="Model", value_vars=["Random split F1", "Unseen-merchant F1"],
                     var_name="Evaluation", value_name="Macro F1")
    fig, ax = _fig(7, 3.8)
    sns.barplot(data=m, x="Model", y="Macro F1", hue="Evaluation", ax=ax)
    ax.set(ylim=(0, 1.05), xlabel="", title="Same models, two evaluation schemes")
    for c in ax.containers:
        ax.bar_label(c, fmt="%.2f", fontsize=8, padding=2)
    fig.tight_layout()
    return fig
