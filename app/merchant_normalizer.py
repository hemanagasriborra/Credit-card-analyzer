"""
merchant_normalizer.py
-----------------------
Solves Bottleneck 1: merchant descriptors are truncated and cryptic.

e.g. "SQ *BLUE BOTTLE COF"  -> "Blue Bottle Coffee"
     "AMZN Mktp IN*2K4TB9"  -> "Amazon"
     "TST*DOMINOS 0234 BLR" -> "Domino's Pizza"

Strategy:
  1. Strip known payment-processor / POS prefixes and junk tokens
     (store codes, city codes, trailing numbers).
  2. Fuzzy-match the cleaned string against a merchant reference table.
  3. Cache every resolution so repeat descriptors are instant on
     future statements (no repeated LLM/fuzzy work).
"""

import re
import json
import os
import pandas as pd
from rapidfuzz import process, fuzz

CACHE_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'descriptor_cache.json')
REFERENCE_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'merchant_categories.csv')

# Common payment-processor / POS prefixes seen on statements
PREFIX_PATTERNS = [
    r'^SQ\s*\*', r'^TST\*', r'^PAYPAL\s*\*', r'^PP\*', r'^AMZN\s*Mktp\s*IN\*?',
    r'^AMZN\s*Mktp\*?', r'^GOOGLE\s*\*', r'^APPLE\.COM/BILL', r'^SP\s*\*',
    r'^WWW\.', r'^POS\s*', r'^UPI[-/]', r'^IN\*',
]

# Trailing junk: store numbers, city/state codes, reference numbers
SUFFIX_PATTERNS = [
    r'\s*\d{3,}$',        # trailing digit codes (store no, ref no)
    r'\s+[A-Z]{2,3}$',    # trailing 2-3 letter city/state code
    r'\*[A-Z0-9]{4,}$',   # trailing order/ref codes after *
]


def _load_reference():
    df = pd.read_csv(REFERENCE_PATH)
    return df


def _load_cache():
    if os.path.exists(CACHE_PATH):
        with open(CACHE_PATH) as f:
            return json.load(f)
    return {}


def _save_cache(cache):
    os.makedirs(os.path.dirname(CACHE_PATH), exist_ok=True)
    with open(CACHE_PATH, 'w') as f:
        json.dump(cache, f, indent=2)


def clean_descriptor(raw: str) -> str:
    """Strip processor prefixes and trailing junk codes."""
    text = raw.strip()
    for pat in PREFIX_PATTERNS:
        text = re.sub(pat, '', text, flags=re.IGNORECASE).strip()
    for pat in SUFFIX_PATTERNS:
        text = re.sub(pat, '', text).strip()
    text = re.sub(r'\s{2,}', ' ', text)
    return text


def resolve_merchant(raw_descriptor: str, reference_df=None, cache=None, threshold=75):
    """
    Returns (merchant_name, category, confidence, source) for a raw descriptor.
    source is one of: 'cache', 'fuzzy_match', 'unmatched'
    """
    if reference_df is None:
        reference_df = _load_reference()
    if cache is None:
        cache = _load_cache()

    key = raw_descriptor.strip().upper()
    if key in cache:
        entry = cache[key]
        return entry['merchant_name'], entry['category'], entry['confidence'], 'cache'

    cleaned = clean_descriptor(raw_descriptor).lower()
    original_lower = raw_descriptor.lower()

    # substring keyword match first (fast, high precision).
    # Check against the ORIGINAL descriptor, not the cleaned one --
    # prefix-stripping (e.g. "AMZN Mktp IN*") can remove the very
    # keyword ("amzn") we're trying to match on.
    for _, row in reference_df.iterrows():
        if row['keyword'] in original_lower or row['keyword'] in cleaned:
            result = (row['merchant_name'], row['category'], 100, 'keyword_match')
            _cache_result(cache, key, result)
            return result

    # fuzzy fallback against merchant names
    choices = reference_df['merchant_name'].tolist()
    match = process.extractOne(cleaned, choices, scorer=fuzz.token_sort_ratio)
    if match and match[1] >= threshold:
        merchant_name = match[0]
        category = reference_df.loc[reference_df['merchant_name'] == merchant_name, 'category'].iloc[0]
        result = (merchant_name, category, match[1], 'fuzzy_match')
        _cache_result(cache, key, result)
        return result

    # unmatched — flag for manual review / LLM fallback
    result = (cleaned.title() if cleaned else raw_descriptor, 'Uncategorized', 0, 'unmatched')
    _cache_result(cache, key, result)
    return result


def _cache_result(cache, key, result):
    merchant_name, category, confidence, source = result
    cache[key] = {'merchant_name': merchant_name, 'category': category, 'confidence': confidence}
    _save_cache(cache)


def normalize_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Add merchant_name, category, match_confidence, match_source columns."""
    reference_df = _load_reference()
    cache = _load_cache()

    merchants, categories, confidences, sources = [], [], [], []
    for raw in df['raw_descriptor']:
        name, cat, conf, src = resolve_merchant(raw, reference_df, cache)
        merchants.append(name)
        categories.append(cat)
        confidences.append(conf)
        sources.append(src)

    df = df.copy()
    df['merchant_name'] = merchants
    df['category'] = categories
    df['match_confidence'] = confidences
    df['match_source'] = sources
    return df


if __name__ == "__main__":
    samples = [
        "SQ *BLUE BOTTLE COF",
        "AMZN Mktp IN*2K4TB9",
        "TST*DOMINOS 0234 BLR",
        "SWIGGY*ORDER 88213",
        "UNKNOWN MERCHANT XYZ 991",
    ]
    for s in samples:
        print(s, "->", resolve_merchant(s))
