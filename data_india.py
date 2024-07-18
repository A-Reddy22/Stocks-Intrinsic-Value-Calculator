import tkinter as tk
from tkinter import messagebox
from bs4 import BeautifulSoup
import pandas as pd
import requests

# Function to fetch and display data from a specific table
def fetch_table_data(soup, table_title):
    section = soup.find(lambda tag: tag.name == "h2" and table_title in tag.text)
    if not section:
        print(f"{table_title} table not found")
        return pd.DataFrame()
    
    table = section.find_next("table", {"class": "data-table"})
    if not table:
        print(f"{table_title} table not found")
        return pd.DataFrame()
    
    rows = table.find_all("tr")
    data_list = []
    
    headers = [header.text.strip() for header in rows[0].find_all("th")]
    
    for row in rows[1:]:
        columns = row.find_all("td")
        data = [col.text.strip().replace(",", "") for col in columns]  # Remove commas
        data_list.append(data)
    
    df = pd.DataFrame(data_list, columns=headers)
    return df

# Function to calculate Free Cash Flow (FCF)
def calculate_fcf(operating_cash_flow, capital_expenditures):
    fcf = [ocf - capex for ocf, capex in zip(operating_cash_flow, capital_expenditures)]
    return fcf

# Function to calculate growth rates
def calculate_growth(values):
    growth_rates = [(values[i] - values[i - 1]) / abs(values[i - 1]) * 100 for i in range(1, len(values))]
    return growth_rates

# Function to calculate the average growth rate over a period
def average_growth_rate(values):
    growth_rates = calculate_growth(values)
    if growth_rates:
        return sum(growth_rates) / len(growth_rates)
    return None

# Function to fetch and show Free Cash Flow (FCF), earnings, revenue, and their growth
def fetch_and_show_financials(ticker):
    stock_url = f"https://www.screener.in/company/{ticker}/consolidated/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    response = requests.get(stock_url, headers=headers)
    if response.status_code != 200:
        print("Failed to retrieve the stock data")
        return None
    
    soup = BeautifulSoup(response.content, "html.parser")
    
    # Extract the Cash Flow table
    cash_flow_df = fetch_table_data(soup, "Cash Flows")
    if cash_flow_df.empty:
        print("Cash Flow table not found")
        return None
    
    # Extract the Profit & Loss table
    pnl_df = fetch_table_data(soup, "Profit & Loss")
    if pnl_df.empty:
        print("Profit & Loss table not found")
        return None
    
    # Normalize column names to make them case-insensitive and trimmed
    cash_flow_df.columns = cash_flow_df.columns.str.strip().str.lower()
    pnl_df.columns = pnl_df.columns.str.strip().str.lower()
    
    # Extract relevant columns
    try:
        operating_cash_flow = cash_flow_df.loc[
            cash_flow_df.iloc[:, 0].str.contains("cash from operating activity", case=False)
        ].iloc[0, 1:].astype(float).tolist()
        
        capital_expenditures = cash_flow_df.loc[
            cash_flow_df.iloc[:, 0].str.contains("cash from investing activity", case=False)
        ].iloc[0, 1:].astype(float).tolist()
        
        revenue = pnl_df.loc[
            pnl_df.iloc[:, 0].str.contains("sales", case=False)
        ].iloc[0, 1:].astype(float).tolist()
        
        earnings = pnl_df.loc[
            pnl_df.iloc[:, 0].str.contains("net profit", case=False)
        ].iloc[0, 1:].astype(float).tolist()
    except KeyError as e:
        print(f"Missing data in table: {e}")
        return None
    
    # Calculate FCF
    fcf = calculate_fcf(operating_cash_flow, capital_expenditures)
    
    # Return data for DCF calculation
    years = cash_flow_df.columns[1:].tolist()  # Skip the first column which is labels
    return years[-5:], revenue[-5:], earnings[-5:], fcf[-5:]

# Function to calculate the DCF value
def calculate_dcf(revenue_growth_rate, fcf_percentage_of_revenue, discount_rate, years, revenue):
    terminal_growth_rate = 0.025  # 2.5% terminal growth rate

    # Project future revenue
    projected_revenue = [revenue[-1] * (1 + revenue_growth_rate / 100) ** i for i in range(1, 6)]
    # Calculate future FCF based on projected revenue
    projected_fcf = [rev * (fcf_percentage_of_revenue / 100) for rev in projected_revenue]

    # Calculate the present value of future FCFs
    discounted_fcf = [fcf / (1 + discount_rate / 100) ** i for i, fcf in enumerate(projected_fcf, start=1)]

    # Calculate terminal value
    terminal_value = projected_fcf[-1] * (1 + terminal_growth_rate) / (discount_rate / 100 - terminal_growth_rate)
    discounted_terminal_value = terminal_value / (1 + discount_rate / 100) ** 5

    # Sum of discounted FCFs and terminal value
    dcf_value = sum(discounted_fcf) + discounted_terminal_value
    
    return dcf_value

# GUI implementation
def fetch_financials_gui():
    ticker = ticker_entry.get().strip().upper()
    data = fetch_and_show_financials(ticker)
    if data:
        years, revenue, earnings, fcf = data
        
        avg_revenue_growth_5yr = average_growth_rate(revenue)
        if avg_revenue_growth_5yr is not None:
            revenue_growth_label.config(text=f"Revenue Growth (5yr): {avg_revenue_growth_5yr:.2f}%")
        else:
            revenue_growth_label.config(text="Revenue Growth data not available")
        
        avg_earnings_growth_5yr = average_growth_rate(earnings)
        if avg_earnings_growth_5yr is not None:
            earnings_growth_label.config(text=f"Earnings Growth (5yr): {avg_earnings_growth_5yr:.2f}%")
        else:
            earnings_growth_label.config(text="Earnings Growth data not available")
        
        fcf_percentage_of_revenue_last_5yrs = [(f / r) * 100 for f, r in zip(fcf, revenue)]
        avg_fcf_percentage_of_revenue = sum(fcf_percentage_of_revenue_last_5yrs) / 5
        
        fcf_percentage_label.config(text=f"FCF as a percentage of Revenue (last 5 yrs): {avg_fcf_percentage_of_revenue:.2f}%")
        
        # Enable the DCF calculation inputs
        revenue_growth_rate_entry.config(state='normal')
        fcf_percentage_of_revenue_entry.config(state='normal')
        discount_rate_entry.config(state='normal')
        calculate_button.config(state='normal')
    else:
        messagebox.showerror("Error", "Failed to retrieve financial data")

def calculate_dcf_gui():
    revenue_growth_rate = float(revenue_growth_rate_entry.get().strip())
    fcf_percentage_of_revenue = float(fcf_percentage_of_revenue_entry.get().strip())
    discount_rate = float(discount_rate_entry.get().strip())
    
    data = fetch_and_show_financials(ticker_entry.get().strip().upper())
    if data:
        years, revenue, earnings, fcf = data
        
        dcf_value = calculate_dcf(revenue_growth_rate, fcf_percentage_of_revenue, discount_rate, years, revenue)
        
        result_label.config(text=f"Intrinsic Value: {dcf_value:.2f} INR - Crores")
    else:
        messagebox.showerror("Error", "Failed to retrieve financial data")

# Main GUI window
root = tk.Tk()
root.title("DCF Calculator")

tk.Label(root, text="NSE Ticker Symbol:").grid(row=0, column=0, padx=10, pady=5)
ticker_entry = tk.Entry(root)
ticker_entry.grid(row=0, column=1, padx=10, pady=5)

fetch_button = tk.Button(root, text="Fetch Financials", command=fetch_financials_gui)
fetch_button.grid(row=1, column=0, columnspan=2, pady=10)

revenue_growth_label = tk.Label(root, text="")
revenue_growth_label.grid(row=2, column=0, columnspan=2, pady=5)

earnings_growth_label = tk.Label(root, text="")
earnings_growth_label.grid(row=3, column=0, columnspan=2, pady=5)

fcf_percentage_label = tk.Label(root, text="")
fcf_percentage_label.grid(row=4, column=0, columnspan=2, pady=5)

tk.Label(root, text="Expected Revenue Growth Rate (%):").grid(row=5, column=0, padx=10, pady=5)
revenue_growth_rate_entry = tk.Entry(root, state='disabled')
revenue_growth_rate_entry.grid(row=5, column=1, padx=10, pady=5)

tk.Label(root, text="FCF as a Percentage of Revenue (%):").grid(row=6, column=0, padx=10, pady=5)
fcf_percentage_of_revenue_entry = tk.Entry(root, state='disabled')
fcf_percentage_of_revenue_entry.grid(row=6, column=1, padx=10, pady=5)

tk.Label(root, text="Discount Rate (%):").grid(row=7, column=0, padx=10, pady=5)
discount_rate_entry = tk.Entry(root, state='disabled')
discount_rate_entry.grid(row=7, column=1, padx=10, pady=5)

calculate_button = tk.Button(root, text="Calculate DCF", command=calculate_dcf_gui, state='disabled')
calculate_button.grid(row=8, column=0, columnspan=2, pady=10)

result_label = tk.Label(root, text="")
result_label.grid(row=9, column=0, columnspan=2, pady=10)

root.mainloop()
