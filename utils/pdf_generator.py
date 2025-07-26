# utils/pdf_generator.py
from xhtml2pdf import pisa
from flask import render_template
import os

def generate_pdf(data):
    # Render HTML dari template print.html
    html = render_template('print.html', aduan=data)
    pdf_path = 'aduan_report.pdf'

    with open(pdf_path, 'wb') as f:
        pisa.CreatePDF(src=html, dest=f)

    return pdf_path
