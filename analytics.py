import sqlite3
import pandas as pd
import numpy as np

def connection():
    return sqlite3.connect("finance_app.db")

def fetch_transactions(user_id=1):
    conn = connection()
    query = "SELECT * FROM Transactions WHERE User_id = ?"
    df = pd.read_sql_query(query, conn, params=(user_id,))
    conn.close()
    return df

def fetch_portfolio_assets(user_id=1):
    conn = connection()
    query = "SELECT * FROM Portfolio_assets WHERE User_id = ?"
    df = pd.read_sql_query(query, conn, params=(user_id,))
    conn.close()

    if not df.empty:
        df['Total_Investment'] = df['Quantity'] * df['Purchase_price']
        df['Current_Value'] = df['Quantity'] * df['Current_price']
        df['Profit_Loss'] = df['Current_Value'] - df['Total_Investment']
        df['Profit_Loss_Percentage'] = (df['Profit_Loss'] / df['Total_Investment']) * 100

    return df

def get_financial_summary(user_id=1):
    transactions_df = fetch_transactions(user_id=user_id)
    portfolio_df = fetch_portfolio_assets(user_id=user_id)

    total_income = transactions_df[transactions_df['Type'] == 'Income']['Amount'].sum() if not transactions_df.empty else 0.0
    total_expense = transactions_df[transactions_df['Type'] == 'Expense']['Amount'].sum() if not transactions_df.empty else 0.0
    net_savings = total_income - total_expense

    total_investment = portfolio_df['Total_Investment'].sum() if not portfolio_df.empty else 0
    current_value = portfolio_df['Current_Value'].sum() if not portfolio_df.empty else 0
    total_profit_loss = current_value - total_investment
    profit_loss_percentage = (total_profit_loss / total_investment) * 100 if total_investment > 0 else 0

    summary = {
        "Total Income": total_income,
        "Total Expense": total_expense,
        "Net Savings": net_savings,
        "Total Investment": total_investment,
        "Current Value of Portfolio": current_value,
        "Total Profit/Loss": total_profit_loss,
        "Profit/Loss Percentage": profit_loss_percentage
    }

    return summary

def get_spending_by_category(user_id=1):
    transactions_df = fetch_transactions(user_id=user_id)
    if not transactions_df.empty:
        spending_df = transactions_df[transactions_df['Type'] == 'Expense'].groupby('Category')['Amount'].sum().reset_index()
        spending_df = spending_df.sort_values(by='Amount', ascending=False)
        return spending_df  
    return pd.DataFrame(columns=['Category', 'Amount'])