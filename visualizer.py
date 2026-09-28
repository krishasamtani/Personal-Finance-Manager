import matplotlib.pyplot as plt

def plot_spending_chart(spending_data):
    fig, ax = plt.subplots(figsize=(6, 4))
    if not spending_data.empty:
        # Index ko reset karte hain taaki numbers ki jagah proper category names aayein
        spending_df = spending_data.reset_index()
        ax.bar(spending_df['Category'], spending_df['Amount'], color=['#ff9999', '#66b3ff', '#99ff99', '#ffcc99'])
        ax.set_ylabel("Amount (₹)")
        ax.set_xlabel("Category")
        ax.set_title("Expense Breakdown by Category")
        plt.xticks(rotation=45)
    else:
        ax.text(0.5, 0.5, 'No Data Available', horizontalalignment='center', verticalalignment='center')
    return fig

def plot_portfolio_allocation(portfolio_df):
    fig, ax = plt.subplots(figsize=(6, 4))
    if not portfolio_df.empty:
        ax.pie(
            portfolio_df['Current_Value'], 
            labels=portfolio_df['Asset_name'], 
            autopct='%1.1f%%', 
            startangle=140, 
            colors=['#ff9999','#66b3ff','#99ff99','#ffcc99','#c2c2f0']
        )
        ax.set_title("Portfolio Asset Allocation")
    else:
        ax.text(0.5, 0.5, 'No Portfolio Assets Found', horizontalalignment='center', verticalalignment='center')
    return fig

def plot_portfolio_profit_loss(portfolio_df):
    fig, ax = plt.subplots(figsize=(6, 4))
    if not portfolio_df.empty:
        colors = portfolio_df['Profit_Loss'].apply(lambda x: '#2ecc71' if x >= 0 else '#e74c3c')
        ax.bar(portfolio_df['Asset_name'], portfolio_df['Profit_Loss'], color=colors, width=0.5)
        ax.set_ylabel("Profit / Loss (₹)")
        ax.set_xlabel("Assets")
        ax.set_title("Asset-wise Profit & Loss")
        plt.xticks(rotation=45)
    else:
        ax.text(0.5, 0.5, 'No Portfolio Assets Found', horizontalalignment='center', verticalalignment='center')
    return fig

def plot_income_vs_expense_chart(total_income, total_expense):
    fig, ax = plt.subplots(figsize=(6, 4))
    categories = ['Income', 'Expense']
    amounts = [total_income, total_expense]
    colors = ['#2ecc71', '#e74c3c']
    ax.bar(categories, amounts, color=colors, width=0.5)
    ax.set_ylabel("Amount (₹)")
    ax.set_title("Income vs Expense Comparison")
    return fig