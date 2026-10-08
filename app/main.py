"""
main.py
-------
Streamlit dashboard: upload a statement -> parsed, categorized,
FX-merged transactions -> monthly/category charts + subscriptions.

Run with:
    streamlit run app/main.py
"""

import sys
import os
sys.path.append(os.path.dirname(__file__))

import streamlit as st
import pandas as pd

from pdf_parser import parse_pdf, parse_csv
from merchant_normalizer import normalize_dataframe
from fx_handler import merge_fx_rows
from subscription_detector import detect_subscriptions
from visualizer import monthly_spend_summary, category_spend_summary, total_fx_fees, \
    plot_monthly_spend, plot_category_spend

st.set_page_config(page_title="Credit Card Statement Analyser", layout="wide")
st.title("💳 Credit Card Statement Analyser & Spend Categoriser")

input_mode = st.radio(
    "How do you want to provide transaction data?",
    ["Upload a statement (PDF/CSV)", "Use bundled sample data", "Enter transactions manually"],
    horizontal=True,
)

df = None

# ---------------------------------------------------------------
# MODE 1: File upload
# ---------------------------------------------------------------
if input_mode == "Upload a statement (PDF/CSV)":
    uploaded = st.file_uploader("Upload a statement (PDF or CSV)", type=["pdf", "csv"])
    if uploaded is not None:
        import tempfile
        temp_path = os.path.join(tempfile.gettempdir(), uploaded.name)
        with open(temp_path, "wb") as f:
            f.write(uploaded.getbuffer())
        if uploaded.name.lower().endswith(".pdf"):
            df = parse_pdf(temp_path)
        else:
            df = parse_csv(temp_path)

# ---------------------------------------------------------------
# MODE 2: Bundled sample data
# ---------------------------------------------------------------
elif input_mode == "Use bundled sample data":
    sample_path = os.path.join(os.path.dirname(__file__), '..', 'sample_data', 'sample_statement.csv')
    df = parse_csv(sample_path)

# ---------------------------------------------------------------
# MODE 3: Manual entry — type in one transaction at a time,
# accumulate them in session state, and run the SAME pipeline
# (fx merge -> categorize -> charts) on whatever has been entered.
# ---------------------------------------------------------------
elif input_mode == "Enter transactions manually":
    st.subheader("Add a Transaction")

    if "manual_transactions" not in st.session_state:
        st.session_state.manual_transactions = []

    with st.form("manual_entry_form", clear_on_submit=True):
        col1, col2, col3, col4 = st.columns([1.2, 2.5, 1, 1])
        with col1:
            entry_date = st.date_input("Date")
        with col2:
            entry_descriptor = st.text_input("Raw descriptor (as it appears on the statement)",
                                              placeholder="e.g. SQ *BLUE BOTTLE COF SF US")
        with col3:
            entry_amount = st.number_input("Amount", min_value=0.0, step=1.0, format="%.2f")
        with col4:
            entry_foreign = st.checkbox("Foreign txn?")
        submitted = st.form_submit_button("➕ Add Transaction")

        if submitted:
            if not entry_descriptor.strip():
                st.warning("Please enter a descriptor before adding the transaction.")
            else:
                st.session_state.manual_transactions.append({
                    "date": entry_date,
                    "raw_descriptor": entry_descriptor.strip(),
                    "amount": entry_amount,
                    "is_foreign": entry_foreign,
                })

    if st.session_state.manual_transactions:
        st.caption(f"{len(st.session_state.manual_transactions)} transaction(s) entered so far:")
        st.dataframe(pd.DataFrame(st.session_state.manual_transactions), use_container_width=True)
        if st.button("🗑️ Clear all entered transactions"):
            st.session_state.manual_transactions = []
            st.rerun()

        df = pd.DataFrame(st.session_state.manual_transactions)
    else:
        st.info("Add at least one transaction above to see it processed below.")

if df is not None and not df.empty:
    st.success(f"Parsed {len(df)} raw transaction rows.")

    with st.spinner("Merging foreign-currency fee rows..."):
        df = merge_fx_rows(df)

    with st.spinner("Categorizing merchants..."):
        df = normalize_dataframe(df)

    tab1, tab2, tab3, tab4 = st.tabs(["Transactions", "Monthly Spend", "By Category", "Subscriptions"])

    with tab1:
        st.subheader("Cleaned Transactions")
        display_cols = ['date', 'raw_descriptor', 'merchant_name', 'category',
                         'base_amount', 'fx_fee', 'total_amount', 'match_source']
        display_cols = [c for c in display_cols if c in df.columns]
        st.dataframe(df[display_cols], use_container_width=True)
        st.caption(f"Total FX fees paid this period: {total_fx_fees(df)}")

        low_conf = df[df['match_confidence'] < 75] if 'match_confidence' in df.columns else pd.DataFrame()
        if not low_conf.empty:
            st.warning(f"{len(low_conf)} transactions had low-confidence merchant matches — review these:")
            st.dataframe(low_conf[['raw_descriptor', 'merchant_name', 'match_confidence']])

    with tab2:
        st.subheader("Monthly Spend")
        st.bar_chart(monthly_spend_summary(df).set_index('month'))

    with tab3:
        st.subheader("Spend by Category")
        st.bar_chart(category_spend_summary(df).set_index('category'))

    with tab4:
        st.subheader("Detected Recurring Subscriptions")
        subs = detect_subscriptions(df)
        if subs.empty:
            st.info("No recurring subscriptions detected yet — need at least 2 occurrences of a merchant.")
        else:
            st.dataframe(subs, use_container_width=True)
            st.caption(f"Estimated monthly subscription spend: {subs[subs['likely_frequency']=='Monthly']['avg_amount'].sum():.2f}")
elif input_mode != "Enter transactions manually":
    st.info("Upload a statement or switch to sample data to get started.")
