"""Central configuration for FinTrack."""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = Path(os.environ.get("FINANCE_DB", BASE_DIR / "finance_app.db"))
MODEL_DIR = BASE_DIR / "models"

BASE_CURRENCY = "INR"
CURRENCY_SYMBOL = "₹"
SUPPORTED_CURRENCIES = ["INR", "USD", "EUR", "GBP"]

EXPENSE_CATEGORIES = [
    "Food", "Groceries", "Rent", "Utilities", "Entertainment", "Investment",
    "Transport", "Shopping", "Health", "Education", "Travel", "Other",
]
INCOME_CATEGORIES = ["Salary", "Freelance", "Interest", "Refund"]
ALL_CATEGORIES = EXPENSE_CATEGORIES + INCOME_CATEGORIES


def category_type(category: str) -> str:
    """The transaction type is derived from the category."""
    return "Income" if category in INCOME_CATEGORIES else "Expense"
