"""
generate_realistic_pdf.py
---------------------------
Builds a PDF version of realistic_demo_statement.csv, laid out like a
real bank statement table, for testing the PDF-parsing path end to end.
"""

import csv
import os
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

CSV_PATH = os.path.join(os.path.dirname(__file__), "realistic_demo_statement.csv")
PDF_PATH = os.path.join(os.path.dirname(__file__), "realistic_demo_statement.pdf")


def load_transactions():
    rows = []
    with open(CSV_PATH) as f:
        reader = csv.DictReader(f)
        for r in reader:
            date = r["date"]
            desc = r["description"]
            amount = float(r["amount"])
            dr_cr = "Cr" if amount < 0 else "Dr"
            amount_str = f"{abs(amount):,.2f}"
            rows.append((date, desc, amount_str, dr_cr))
    return rows


def build_pdf():
    transactions = load_transactions()
    c = canvas.Canvas(PDF_PATH, pagesize=letter)
    width, height = letter
    y = height - 72

    def new_page_header():
        nonlocal y
        c.setFont("Helvetica-Bold", 14)
        c.drawString(72, y, "SAMPLE BANK  |  Credit Card Statement")
        y -= 20
        c.setFont("Helvetica", 9)
        c.drawString(72, y, "Statement Period: 01 Apr 2026 - 30 Jun 2026    Card ending: 7734")
        y -= 30
        c.setFont("Courier-Bold", 9)
        c.drawString(72, y, "Date        Description                          Amount")
        y -= 4
        c.line(72, y, 540, y)
        y -= 14
        c.setFont("Courier", 9)

    new_page_header()
    for date, descriptor, amount, dr_cr in transactions:
        line = f"{date}   {descriptor:<38}{amount:>10} {dr_cr}"
        c.drawString(72, y, line)
        y -= 14
        if y < 72:
            c.showPage()
            y = height - 72
            new_page_header()

    c.save()
    print(f"Generated {PDF_PATH} with {len(transactions)} transactions.")


if __name__ == "__main__":
    build_pdf()
