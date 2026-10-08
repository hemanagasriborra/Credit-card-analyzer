"""
subscription_detector.py
-------------------------
Detects recurring subscriptions by grouping transactions per merchant
and checking for regular time intervals + consistent amounts.
"""

import pandas as pd
import numpy as np


def detect_subscriptions(df: pd.DataFrame, min_occurrences=2,
                          interval_tolerance_days=5, amount_tolerance_pct=0.1) -> pd.DataFrame:
    """
    df must have: date, merchant_name, total_amount (or amount)
    Returns a DataFrame: merchant_name, occurrences, avg_amount,
    avg_interval_days, likely_frequency, confidence, next_expected_date
    """
    amount_col = 'total_amount' if 'total_amount' in df.columns else 'amount'
    df = df[df[amount_col] > 0].copy()  # ignore payments/refunds (negative)
    results = []

    for merchant, group in df.groupby('merchant_name'):
        group = group.sort_values('date')
        if len(group) < min_occurrences:
            continue

        dates = group['date'].tolist()
        amounts = group[amount_col].tolist()

        gaps = [(dates[i + 1] - dates[i]).days for i in range(len(dates) - 1)]
        if not gaps:
            continue

        avg_gap = np.mean(gaps)
        gap_std = np.std(gaps)
        avg_amount = np.mean(amounts)
        amount_std = np.std(amounts)

        # regularity checks
        gap_is_regular = gap_std <= interval_tolerance_days
        amount_is_regular = (amount_std / avg_amount if avg_amount else 1) <= amount_tolerance_pct

        if not (gap_is_regular and 20 <= avg_gap <= 400):
            continue  # not a recurring pattern we recognize

        frequency = _classify_frequency(avg_gap)
        confidence = _confidence_score(gap_is_regular, amount_is_regular, len(group))

        results.append({
            'merchant_name': merchant,
            'occurrences': len(group),
            'avg_amount': round(avg_amount, 2),
            'avg_interval_days': round(avg_gap, 1),
            'likely_frequency': frequency,
            'confidence': confidence,
            'last_charge_date': dates[-1],
            'next_expected_date': dates[-1] + pd.Timedelta(days=round(avg_gap)),
        })

    if not results:
        # No merchant had enough occurrences yet (e.g. only 1-2 transactions
        # entered so far). Return an empty DataFrame with the right columns
        # instead of one with zero columns -- otherwise sort_values('confidence')
        # below fails with a KeyError, since the column doesn't exist yet.
        return pd.DataFrame(columns=[
            'merchant_name', 'occurrences', 'avg_amount', 'avg_interval_days',
            'likely_frequency', 'confidence', 'last_charge_date', 'next_expected_date',
        ])

    return pd.DataFrame(results).sort_values('confidence', ascending=False)


def _classify_frequency(avg_gap_days):
    if 25 <= avg_gap_days <= 35:
        return 'Monthly'
    if 80 <= avg_gap_days <= 100:
        return 'Quarterly'
    if 350 <= avg_gap_days <= 380:
        return 'Annual'
    if 6 <= avg_gap_days <= 8:
        return 'Weekly'
    return f'~every {round(avg_gap_days)} days'


def _confidence_score(gap_regular, amount_regular, occurrences):
    score = 0.4 * gap_regular + 0.4 * amount_regular + 0.2 * min(occurrences / 4, 1)
    return round(score * 100, 1)
