import streamlit as st
import pandas as pd
from fpdf import FPDF
import pdfplumber
import tempfile

def extract_amount_from_pdf(file):
    with pdfplumber.open(file) as pdf:
        text = "\n".join([page.extract_text() for page in pdf.pages if page.extract_text()])
    lines = text.split("\n")
    for line in reversed(lines):
        if any(keyword in line.lower() for keyword in ["betrag", "gesamt", "total"]):
            for word in line.split():
                word_clean = word.replace(".", "").replace(",", ".").replace("€", "")
                try:
                    val = float(word_clean)
                    return round(val, 2)
                except:
                    continue
    return None

def format_de_eur(value):
    if pd.isna(value) or value is None:
        return ""
    return f"{value:,.2f} EUR".replace(",", "X").replace(".", ",").replace("X", ".")

class PDF(FPDF):
    def __init__(self, mietername, adresse, vertragsnummer):
        super().__init__()
        self.mietername = mietername
        self.adresse = adresse
        self.vertragsnummer = vertragsnummer

    def header(self):
        self.set_font("Helvetica", "B", 12)
        self.cell(0, 10, self.mietername)
        self.ln()
        self.set_font("Helvetica", "", 10)
        self.cell(0, 8, self.adresse)
        self.ln()
        self.set_font("Helvetica", "I", 10)
        self.cell(0, 8, "Die Beträge sind brutto.")
        self.ln(8)

def create_payment_plan(miete, werbung, gastro):
    monate = ["Januar", "Februar", "März", "April", "Mai", "Juni", "Juli", "August", "September", "Oktober", "November", "Dezember"]
    rows = []
    for monat in monate:
        wb = werbung if monat in ["Januar", "Juli"] else None
        row = [monat, miete, wb, gastro if gastro is not None else None, sum(filter(None, [miete, wb, gastro]))]
        rows.append(row)
    return pd.DataFrame(rows, columns=["Monat", "Miete + Nebenkosten", "Werbebeitrag", "Gastro (Fettabluft)", "Monatlich insgesamt"])

def generate_pdf(df, mietername, adresse, vertragsnummer):
    pdf = PDF(mietername, adresse, vertragsnummer)
    pdf.add_page()

    spalten = df.columns.tolist()
    breiten = [30, 40, 40, 40, 40]

    pdf.set_font("Helvetica", "B", 9)
    for i, col in enumerate(spalten):
        pdf.cell(breiten[i], 8, col, border=1, align="C")
    pdf.ln()

    pdf.set_font("Helvetica", "", 9)
    for _, row in df.iterrows():
        werte = [
            str(row["Monat"]),
            format_de_eur(row["Miete + Nebenkosten"]),
            format_de_eur(row["Werbebeitrag"]),
            format_de_eur(row.get("Gastro (Fettabluft)", None)),
            format_de_eur(row["Monatlich insgesamt"])
        ]
        for i, val in enumerate(werte):
            pdf.cell(breiten[i], 8, val, border=1, align="C")
        pdf.ln()

    pdf.ln(6)
    pdf.set_font("Helvetica", "", 9)

    konto_infos = f"""Zahlungsempfänger & Kontoverbindungen:

1. Miete + Nebenkosten - HBB Gewerbebau Projektgesellschaft
IBAN: DE94 1003 0200 1052 5300 42
BIC: BHYPDEB2XXX
Bank: Berlin Hyp
Verwendungszweck: {vertragsnummer}

2. Werbebeiträge - HBB Centermanagement GmbH & Co. KG
IBAN: DE39 2005 0550 1002 2985 84
BIC: HASPDEHHXXX
Bank: Hamburger Sparkasse
Verwendungszweck: {vertragsnummer}
"""".strip()

    if df["Gastro (Fettabluft)"].notna().any():
        konto_infos += f"""

3. Gastro - HBB Betreuungsgesellschaft mbH
IBAN: DE56 2005 0550 1002 2562 77
BIC: HASPDEHHXXX
Bank: Hamburger Sparkasse
"""".strip()

    for line in konto_infos.strip().split("\n"):
        pdf.multi_cell(180, 6, line.strip(), align="L")

    temp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    pdf.output(temp.name)
    return temp.name

# === STREAMLIT INTERFACE ===
st.set_page_config(page_title="Zahlungsplan Generator")
st.title("📄 Zahlungsplan Generator")

mietername = st.text_input("Mietername")
adresse = st.text_input("Adresse")
vertragsnummer = st.text_input("Vertragsnummer")
uploaded_files = st.file_uploader("Rechnungen (PDF)", type="pdf", accept_multiple_files=True)

col1, col2, col3 = st.columns(3)
with col1:
    miete = st.number_input("Monatlich: Miete + Nebenkosten", min_value=0.0, format="%.2f")
with col2:
    werbung = st.number_input("Halbjährlich: Werbebeitrag", min_value=0.0, format="%.2f")
with col3:
    gastro = st.number_input("Monatlich: Gastro (Fettabluft)", min_value=0.0, format="%.2f")

if st.button("PDF erzeugen"):
    df = create_payment_plan(miete, werbung, gastro if gastro > 0 else None)
    pfad = generate_pdf(df, mietername, adresse, vertragsnummer)

    st.success("✅ PDF wurde erfolgreich erstellt!")
    with open(pfad, "rb") as f:
        st.download_button("📥 PDF herunterladen", f, file_name="Zahlungsplan.pdf", mime="application/pdf")