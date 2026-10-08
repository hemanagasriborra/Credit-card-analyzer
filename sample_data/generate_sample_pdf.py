"""
generate_sample_pdf.py
------------------------
Creates a realistic-looking sample credit card statement PDF for testing
the PDF parsing path (app/pdf_parser.py). Row format matches ROW_REGEX:
    DATE   DESCRIPTOR   AMOUNT[Dr/Cr]
"""

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

TRANSACTIONS = [
    ("01/05/2026", "SWIGGY*ORDER 88213",              "450.00", "Dr"),
    ("02/05/2026", "NETFLIX.COM",                      "649.00", "Dr"),
    ("03/05/2026", "SQ *BLUE BOTTLE COF SF US",         "320.00", "Dr"),
    ("03/05/2026", "FOREIGN CURRENCY MARKUP FEE",         "9.60", "Dr"),
    ("05/05/2026", "AMZN Mktp IN*2K4TB9",             "1,299.00", "Dr"),
    ("07/05/2026", "UBER *TRIP HELP.UBER.COM",          "180.00", "Dr"),
    ("10/05/2026", "BIGBASKET ONLINE 4471",           "2,150.00", "Dr"),
    ("12/05/2026", "SPOTIFY INDIA",                     "119.00", "Dr"),
    ("15/05/2026", "TST*DOMINOS 0234 BLR",              "899.00", "Dr"),
    ("18/05/2026", "APPLE.COM/BILL",                    "199.00", "Dr"),
    ("20/05/2026", "UNKNOWN MERCHANT XYZ 991",          "750.00", "Dr"),
    ("22/05/2026", "PAYMENT RECEIVED - THANK YOU",    "5,000.00", "Cr"),
    ("01/06/2026", "SWIGGY*ORDER 90144",                "410.00", "Dr"),
    ("02/06/2026", "NETFLIX.COM",                       "649.00", "Dr"),
    ("06/06/2026", "SQ *BLUE BOTTLE COF SF US",         "340.00", "Dr"),
    ("06/06/2026", "FOREIGN CURRENCY MARKUP FEE",        "10.20", "Dr"),
    ("12/06/2026", "SPOTIFY INDIA",                     "119.00", "Dr"),
    ("15/06/2026", "BIGBASKET ONLINE 4471",           "1,980.00", "Dr"),
    ("18/06/2026", "APPLE.COM/BILL",                    "199.00", "Dr"),
]


def build_pdf(path="sample_statement.pdf"):
    c = canvas.Canvas(path, pagesize=letter)
    width, height = letter
    y = height - 72

    c.setFont("Helvetica-Bold", 14)
    c.drawString(72, y, "SAMPLE BANK  |  Credit Card Statement")
    y -= 20
    c.setFont("Helvetica", 9)
    c.drawString(72, y, "Statement Period: 01 May 2026 - 30 Jun 2026    Card ending: 4471")
    y -= 30

    c.setFont("Courier-Bold", 9)
    c.drawString(72, y, "Date        Description                          Amount")
    y -= 4
    c.line(72, y, 540, y)
    y -= 14

    c.setFont("Courier", 9)
    for date, descriptor, amount, dr_cr in TRANSACTIONS:
        line = f"{date}   {descriptor:<38}{amount:>10} {dr_cr}"
        c.drawString(72, y, line)
        y -= 14
        if y < 72:
            c.showPage()
            c.setFont("Courier", 9)
            y = height - 72

    c.save()


if __name__ == "__main__":
    build_pdf()
    print("Sample PDF statement generated.")
