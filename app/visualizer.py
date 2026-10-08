"""
visualizer.py
-------------
Builds summary tables and matplotlib charts for:
  - Monthly total spend
  - Spend by category
  - FX fees paid over time
"""

import pandas as pd
import matplotlib.pyplot as plt


def monthly_spend_summary(df: pd.DataFrame) -> pd.DataFrame:
    amount_col = 'total_amount' if 'total_amount' in df.columns else 'amount'
    d = df.copy()
    d = d[d[amount_col] > 0]
    d['month'] = pd.to_datetime(d['date']).dt.to_period('M').astype(str)
    return d.groupby('month')[amount_col].sum().reset_index().rename(columns={amount_col: 'total_spend'})


def category_spend_summary(df: pd.DataFrame) -> pd.DataFrame:
    amount_col = 'total_amount' if 'total_amount' in df.columns else 'amount'
    d = df.copy()
    d = d[d[amount_col] > 0]
    return d.groupby('category')[amount_col].sum().reset_index() \
             .rename(columns={amount_col: 'total_spend'}) \
             .sort_values('total_spend', ascending=False)


def total_fx_fees(df: pd.DataFrame) -> float:
    if 'fx_fee' not in df.columns:
        return 0.0
    return round(df['fx_fee'].sum(), 2)


def plot_monthly_spend(df: pd.DataFrame, save_path=None):
    summary = monthly_spend_summary(df)
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.bar(summary['month'], summary['total_spend'], color='#4C72B0')
    ax.set_title('Monthly Spend')
    ax.set_ylabel('Amount')
    ax.set_xlabel('Month')
    plt.xticks(rotation=45)
    plt.tight_layout()
    if save_path:
        plt.savefig(save_path)
    return fig


def plot_category_spend(df: pd.DataFrame, save_path=None):
    summary = category_spend_summary(df)
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.barh(summary['category'], summary['total_spend'], color='#DD8452')
    ax.set_title('Spend by Category')
    ax.set_xlabel('Amount')
    plt.tight_layout()
    if save_path:
        plt.savefig(save_path)
    return fig
