# Credit Card Statement Analyser & Spend Categoriser

An end-to-end tool that parses credit card statement PDFs/CSVs, cleans up
cryptic truncated merchant descriptors, correctly merges foreign-currency
markup fee rows into their parent transaction, categorises spend, detects
recurring subscriptions, and charts monthly spend — all in an interactive
Streamlit dashboard.

---

## 1. Project structure

```
statement_analyser/
├── requirements.txt
├── README.md
├── app/
│   ├── pdf_parser.py            # extracts raw rows from PDF/CSV statements
│   ├── merchant_normalizer.py   # cleans + categorises cryptic descriptors
│   ├── fx_handler.py            # merges foreign-currency fee rows
│   ├── subscription_detector.py # detects recurring subscriptions
│   ├── visualizer.py            # builds spend summaries/charts
│   └── main.py                  # Streamlit dashboard (entry point)
├── data/
│   └── merchant_categories.csv  # seed merchant -> category reference table
│   └── descriptor_cache.json    # auto-created cache of resolved merchants
└── sample_data/
    └── sample_statement.csv     # test data so you can run it immediately
```

---

## 2. Requirements to install

You need **Python 3.9+**. Then, from inside the `statement_analyser` folder:

```bash
python3 -m venv venv
source venv/bin/activate        # on Windows: venv\Scripts\activate

pip install -r requirements.txt
```

This installs:
- `pandas` – data wrangling
- `pdfplumber` – PDF table/text extraction
- `rapidfuzz` – fuzzy string matching for merchant names
- `matplotlib` – charts
- `streamlit` – the dashboard UI
- `python-dateutil` – flexible date parsing

---

## 3. How to run it

```bash
streamlit run app/main.py
```

This opens a browser tab. Tick **"Use bundled sample data"** to see it work
immediately with the included `sample_data/sample_statement.csv`, or upload
your own statement (PDF or CSV).

> **Tip:** Most banks let you export your statement as CSV from netbanking —
> this is far more reliable to parse than a PDF, since PDF table layouts
> vary a lot bank to bank. Use CSV first if you have the option.

---

## 4. How each bottleneck is solved

### Bottleneck 1 — Truncated, cryptic merchant descriptors
`app/merchant_normalizer.py`:
1. Strips known payment-processor/POS prefixes (`SQ *`, `TST*`, `AMZN Mktp IN*`, `PAYPAL *`, etc.) and trailing junk (store codes, ref numbers).
2. Matches the **original** descriptor (not just the cleaned one — prefix-stripping can accidentally remove the keyword you need, e.g. "amzn") against a keyword table in `data/merchant_categories.csv`.
3. Falls back to fuzzy string matching (`rapidfuzz`) against known merchant names.
4. Anything still unmatched is flagged `Uncategorized` with `match_confidence = 0` so you can review and manually correct it — every correction gets cached in `data/descriptor_cache.json` so it's instant next time that exact descriptor appears.

### Bottleneck 2 — Foreign currency markup rows
`app/fx_handler.py`:
1. Flags rows whose descriptor matches fee/markup keywords (`markup`, `foreign currency`, `fx fee`, `conversion fee`, etc).
2. For each fee row, searches backward for the nearest preceding transaction within a small day-gap window and merges them.
3. Outputs one logical transaction per purchase: `base_amount`, `fx_fee`, `total_amount` — so your charts don't double-count or fragment a single purchase into two "merchants."

---

## 5. Extending the project (good next steps for your submission)

- **Improve merchant coverage:** add more rows to `data/merchant_categories.csv` as you encounter uncategorized merchants.
- **MCC-code based categorization:** if your bank's CSV export includes a Merchant Category Code column, prefer that over descriptor guessing — it's far more reliable. Add a `mcc_lookup.py` mapping MCC codes to categories.
- **LLM fallback for the long tail:** for merchants that don't fuzzy-match anything, you could call an LLM API with a prompt like *"Given this truncated card descriptor, return the likely merchant name and spend category"* — cheap, and covers descriptors no static table will ever have.
- **PDF layout robustness:** real bank PDFs vary a lot. If `pdf_parser.py`'s regex doesn't catch your bank's row format, print `page.extract_text()` for a sample page and adjust `ROW_REGEX` in `pdf_parser.py` to match.
- **Export report:** add a button to export the categorized transactions + charts as a PDF/Excel report for submission.

---

## 6. Quick command-line testing (without the dashboard)

You can test each module directly:

```bash
python3 app/pdf_parser.py sample_data/sample_statement.csv
python3 app/merchant_normalizer.py
python3 app/fx_handler.py
```

---

## 7. Troubleshooting

| Problem | Fix |
|---|---|
| `ModuleNotFoundError` | Make sure your virtual environment is activated, then re-run `pip install -r requirements.txt` |
| PDF parses 0 rows | Your bank's PDF layout doesn't match `ROW_REGEX` in `pdf_parser.py` — export CSV instead, or adjust the regex after inspecting `page.extract_text()` output |
| Streamlit won't open | Check the terminal for the local URL (usually `http://localhost:8501`) and open it manually |
| Everything shows "Uncategorized" | Add more keyword rows to `data/merchant_categories.csv` matching your actual statement's merchants |
