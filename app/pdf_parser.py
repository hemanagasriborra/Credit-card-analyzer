"""
pdf_parser.py
-------------
Extracts raw transaction rows from a credit card statement.
Supports:
  - PDF statements (text-based tables) via pdfplumber
  - CSV statements (many banks let you export CSV instead of PDF)

Output: a pandas DataFrame with columns:
    date, raw_descriptor, amount, is_foreign (bool guess)
"""

import re
import pandas as pd
import pdfplumber
from dateutil import parser as dateparser

# A transaction line typically looks like (varies bank to bank):
#   12/05/2026  SQ *BLUE BOTTLE COF        450.00
#   12-May-26   AMZN Mktp IN*2K4TB9        1,299.00 Dr
# We use a fairly loose regex and let downstream cleaning handle it.
DATE_PATTERN = r'(\d{1,2}[/-][A-Za-z0-9]{2,3}[/-]\d{2,4})'
AMOUNT_PATTERN = r'([\d,]+\.\d{2})\s*(Dr|Cr)?'

ROW_REGEX = re.compile(
    rf'{DATE_PATTERN}\s+(.+?)\s+{AMOUNT_PATTERN}\s*$'
)

FOREIGN_HINTS = [
    'fx', 'foreign', 'intl', 'international', 'markup', 'conversion',
    'usd', 'eur', 'gbp', 'cross currency', 'cross-currency'
]


def parse_pdf(filepath: str) -> pd.DataFrame:
    """Extract transaction rows from a PDF credit card statement."""
    rows = []
    with pdfplumber.open(filepath) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            for line in text.split("\n"):
                match = ROW_REGEX.search(line.strip())
                if match:
                    date_str, descriptor, amount_str, dr_cr = match.groups()
                    rows.append(_build_row(date_str, descriptor, amount_str, dr_cr))
    return pd.DataFrame(rows)


def parse_csv(filepath: str, date_col='date', desc_col='description', amount_col='amount') -> pd.DataFrame:
    """Extract transaction rows from a CSV export of a statement."""
    df = pd.read_csv(filepath)
    df = df.rename(columns={date_col: 'date', desc_col: 'raw_descriptor', amount_col: 'amount'})
    df['date'] = df['date'].apply(_safe_date_parse)
    df['amount'] = df['amount'].astype(str).str.replace(',', '').astype(float)
    df['is_foreign'] = df['raw_descriptor'].str.lower().apply(_looks_foreign)
    return df[['date', 'raw_descriptor', 'amount', 'is_foreign']]


def _build_row(date_str, descriptor, amount_str, dr_cr):
    amount = float(amount_str.replace(',', ''))
    if dr_cr and dr_cr.strip().lower() == 'cr':
        amount = -amount  # payment / refund
    return {
        'date': _safe_date_parse(date_str),
        'raw_descriptor': descriptor.strip(),
        'amount': amount,
        'is_foreign': _looks_foreign(descriptor.lower())
    }


def _safe_date_parse(date_str):
    try:
        return dateparser.parse(str(date_str), dayfirst=True).date()
    except Exception:
        return None


def _looks_foreign(descriptor_lower: str) -> bool:
    return any(hint in descriptor_lower for hint in FOREIGN_HINTS)


if __name__ == "__main__":
    import sys
    path = sys.argv[1]
    if path.lower().endswith('.pdf'):
        df = parse_pdf(path)
    else:
        df = parse_csv(path)
    print(df)
