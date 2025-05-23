import streamlit as st
import pandas as pd
from fpdf import FPDF
import tempfile

def format_de_eur(value):
    try:
        val = float(str(value).replace(",", "."))
        return f"{val:,.2f} EUR".replace(",", "X").replace(".", ",").replace("X", ".")
    except:
        return ""

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
        row = [monat, miete, "", wb, "", gastro if gastro is not None else "", "", sum(filter(None, [miete, wb, gastro]))]
        rows.append(row)
    return pd.DataFrame(rows, columns=["Monat", "Miete + Nebenkosten", "Überwiesen", "Werbebeitrag", "Überwiesen2", "Gastro (Fettabluft)", "Überwiesen3", "Monatlich insgesamt"])

def generate_pdf(df, mietername, adresse, vertragsnummer):
    pdf = PDF(mietername, adresse, vertragsnummer)
    pdf.add_page()

    spalten = df.columns.tolist()
    breiten = [30, 32, 20, 32, 20, 32, 20, 34]

    pdf.set_font("Helvetica", "B", 9)
    for i, col in enumerate(spalten):
        pdf.cell(breiten[i], 8, col, border=1, align="C")
    pdf.ln()

    pdf.set_font("Helvetica", "", 9)
    for _, row in df.iterrows():
        werte = [
            str(row["Monat"]),
            format_de_eur(row["Miete + Nebenkosten"]),
            "",
            format_de_eur(row["Werbebeitrag"]),
            "",
            format_de_eur(row["Gastro (Fettabluft)"]) if row["Gastro (Fettabluft)"] else "",
            "",
            format_de_eur(row["Monatlich insgesamt"])
        ]
        for i, val in enumerate(werte):
            pdf.cell(breiten[i], 8, val, border=1, align="C")
        pdf.ln()

    pdf.ln(6)
    pdf.set_font("Helvetica", "", 9)
    kontotext = f'''
Zahlungsempfänger & Kontoverbindungen:

1. Miete + Nebenkosten - Kontoinhaber: HBB Gewerbebau Projektgesellschaft
IBAN: DE94 1003 0200 1052 5300 42
BIC: BHYPDEB2XXX
Bank: Berlin Hyp
Verwendungszweck: {vertragsnummer}

2. Werbebeiträge - Kontoinhaber: HBB Centermanagement GmbH & Co. KG
IBAN: DE39 2005 0550 1002 2985 84
BIC: HASPDEHHXXX
Bank: Hamburger Sparkasse
Verwendungszweck: {vertragsnummer}

3. Gastro - Kontoinhaber: HBB Betreuungsgesellschaft mbH
IBAN: DE56 2005 0550 1002 2562 77
BIC: HASPDEHHXXX
Bank: Hamburger Sparkasse
    '''
    for line in kontotext.strip().split("\n"):
        pdf.multi_cell(180, 6, line.strip(), align="L")

    temp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    pdf.output(temp.name)
    return temp.name

st.set_page_config(page_title="Zahlungsplan Generator", layout="centered")
st.title("📄 Zahlungsplan Generator")

mietername = st.text_input("Mietername", "BK-Süd GmbH / Burger King")
adresse = st.text_input("Adresse", "Raiffeisenstraße 8, 78658 Zimmern")
vertragsnummer = st.text_input("Vertragsnummer", "0080098001")

miete = st.number_input("Monatlich: Miete + Nebenkosten", step=0.01)
werbung = st.number_input("Halbjährlich: Werbebeitrag", step=0.01)
gastro = st.number_input("Monatlich: Gastro (Fettabluft)", step=0.01)

if st.button("PDF erzeugen"):
    df = create_payment_plan(miete, werbung, gastro)
    pfad = generate_pdf(df, mietername, adresse, vertragsnummer)
    with open(pfad, "rb") as f:
        st.download_button("📥 PDF herunterladen", f, file_name="Zahlungsplan.pdf", mime="application/pdf")