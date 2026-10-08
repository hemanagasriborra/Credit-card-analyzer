"""
fx_handler.py
-------------
Solves Bottleneck 2: foreign currency transactions carry separate
markup/fee rows on the statement.

Typical pattern on a statement:
    12/05/2026  BLUE BOTTLE COF SF US        3.50 USD -> 320.00 INR
    12/05/2026  FOREIGN CURRENCY MARKUP FEE               9.60 INR

These are two rows for ONE purchase. If left unmerged, spend charts
double-count the transaction as two separate merchants and the FX
fee gets miscategorized as "Uncategorized" spend instead of being
tagged as a fee tied to that specific purchase.

Strategy:
  1. Flag rows whose descriptor matches known fee/markup keywords.
  2. For each fee row, look for the nearest preceding transaction
     row (within N days, before the fee in statement order) marked
     is_foreign=True, and merge them.
  3. Output one row per logical purchase with:
        base_amount, fx_fee, total_amount, original_currency (if parseable)
"""

import re
import pandas as pd

FEE_KEYWORDS = [
    'markup', 'foreign currency', 'fx fee', 'conversion fee',
    'cross currency', 'cross-currency', 'intl transaction fee',
    'international transaction fee'
]

CURRENCY_REGEX = re.compile(r'\b(USD|EUR|GBP|AED|SGD|AUD|JPY|CAD)\b', re.IGNORECASE)


def is_fee_row(descriptor: str) -> bool:
    d = descriptor.lower()
    return any(kw in d for kw in FEE_KEYWORDS)


def extract_currency(descriptor: str):
    match = CURRENCY_REGEX.search(descriptor)
    return match.group(1).upper() if match else None


def merge_fx_rows(df: pd.DataFrame, max_day_gap: int = 2) -> pd.DataFrame:
    """
    Takes a transaction DataFrame (must have date, raw_descriptor, amount,
    is_foreign columns, sorted by date) and returns a new DataFrame where
    FX fee rows are merged into their parent purchase row.
    """
    df = df.sort_values('date').reset_index(drop=True)
    df['is_fee_row'] = df['raw_descriptor'].apply(is_fee_row)
    df['fx_fee'] = 0.0
    df['original_currency'] = df['raw_descriptor'].apply(extract_currency)

    used_fee_indices = set()

    for i, row in df.iterrows():
        if not row['is_fee_row']:
            continue
        # Search backward for the nearest preceding non-fee row within
        # max_day_gap days. Real statements often only flag "foreign"
        # on the FEE row itself (e.g. "FOREIGN CURRENCY MARKUP FEE"),
        # not on the purchase row, so we can't require is_foreign=True
        # on the candidate. We prefer an is_foreign candidate if one
        # exists in range, but fall back to the nearest non-fee row.
        best_candidate_idx = None
        for j in range(i - 1, -1, -1):
            candidate = df.loc[j]
            if candidate['is_fee_row']:
                continue
            if row['date'] is None or candidate['date'] is None:
                continue
            gap = abs((row['date'] - candidate['date']).days)
            if gap > max_day_gap:
                break  # rows are sorted by date; no closer match further back
            if best_candidate_idx is None:
                best_candidate_idx = j
            if candidate['is_foreign']:
                best_candidate_idx = j
                break  # explicit foreign flag wins outright
        if best_candidate_idx is not None:
            df.at[best_candidate_idx, 'fx_fee'] = row['amount']
            used_fee_indices.add(i)

    merged = df[~df.index.isin(used_fee_indices)].copy()
    merged['base_amount'] = merged['amount']
    merged['total_amount'] = merged['base_amount'] + merged['fx_fee']
    merged = merged.drop(columns=['is_fee_row'])
    return merged.reset_index(drop=True)


if __name__ == "__main__":
    sample = pd.DataFrame([
        {"date": pd.Timestamp("2026-05-12"), "raw_descriptor": "BLUE BOTTLE COF SF US", "amount": 320.00, "is_foreign": True},
        {"date": pd.Timestamp("2026-05-12"), "raw_descriptor": "FOREIGN CURRENCY MARKUP FEE", "amount": 9.60, "is_foreign": False},
        {"date": pd.Timestamp("2026-05-14"), "raw_descriptor": "SWIGGY*ORDER 88213", "amount": 450.00, "is_foreign": False},
    ])
    print(merge_fx_rows(sample))
