import streamlit as st
import pandas as pd
from fpdf import FPDF
import tempfile

st.set_page_config(page_title="Zahlungsplan Generator", layout="centered")

MONATE = [
    "Januar", "Februar", "März", "April", "Mai", "Juni",
    "Juli", "August", "September", "Oktober", "November", "Dezember"
]
BREITEN = [30, 32, 20, 32, 20, 32, 20, 34]

def format_de_eur(value):
    if pd.isna(value):
        return ""
    return f"{value:,.2f} EUR".replace(",", "X").replace(".", ",").replace("X", ".")

def erstelle_pdf(df, mietername, mieteradresse, vertragsnummer):
    class PDF(FPDF):
        def header(self):
            self.set_font("Helvetica", "B", 12)
            self.cell(0, 10, mietername)
            self.ln()
            self.set_font("Helvetica", "", 10)
            self.cell(0, 8, mieteradresse)
            self.ln()
            self.set_font("Helvetica", "I", 10)
            self.cell(0, 8, "Die Beträge sind brutto.")
            self.ln(8)

    pdf = PDF()
    pdf.add_page()

    pdf.set_font("Helvetica", "B", 9)
    for i, col in enumerate(df.columns.tolist()):
        pdf.cell(BREITEN[i], 8, col, border=1, align="C")
    pdf.ln()

    pdf.set_font("Helvetica", "", 9)
    for _, row in df.iterrows():
        werte = [
            str(row["Monat"]),
            format_de_eur(row["Miete + Nebenkosten"]),
            "",
            format_de_eur(row["Werbebeitrag"]),
            "",
            format_de_eur(row["Gastro (Fettabluft)"]),
            "",
            format_de_eur(row["Monatlich insgesamt"])
        ]
        for i, val in enumerate(werte):
            pdf.cell(BREITEN[i], 8, val, border=1, align="C")
        pdf.ln()

    pdf.ln(6)
    pdf.set_font("Helvetica", "", 9)
    zahlungstext = f"""
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
"""
    for line in zahlungstext.strip().splitlines():
        clean = line.strip().replace("–", "-").replace("—", "-")
        if clean:
            pdf.multi_cell(180, 6, clean, align="L")
        else:
            pdf.ln(4)

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        pdf.output(tmp.name)
        return tmp.name

st.title("📄 Zahlungsplan Generator")
with st.form("input_form"):
    st.subheader("Mieterinformationen")
    mietername = st.text_input("Mietername", "BK-Süd GmbH / Burger King")
    mieteradresse = st.text_input("Adresse", "Raiffeisenstraße 8, 78658 Zimmern")
    vertragsnummer = st.text_input("Vertragsnummer", "0080098001")

    st.subheader("Beträge eingeben (brutto)")
    betrag_miete = st.number_input("Monatlich: Miete + Nebenkosten", value=5250.18)
    betrag_werbung = st.number_input("Halbjährlich: Werbebeitrag", value=2178.41)
    betrag_gastro = st.number_input("Monatlich: Gastro (Fettabluft)", value=335.02)

    submitted = st.form_submit_button("PDF erzeugen")

if submitted:
    daten = []
    for monat in MONATE:
        werbung = betrag_werbung if monat in ["Januar", "Juli"] else ""
        daten.append([
            monat,
            betrag_miete,
            "",
            werbung,
            "",
            betrag_gastro,
            "",
            sum(filter(None, [betrag_miete, werbung, betrag_gastro]))
        ])

    df = pd.DataFrame(daten, columns=[
        "Monat", "Miete + Nebenkosten", "Überwiesen",
        "Werbebeitrag", "Überwiesen2", "Gastro (Fettabluft)",
        "Überwiesen3", "Monatlich insgesamt"
    ])

    pfad = erstelle_pdf(df, mietername, mieteradresse, vertragsnummer)
    st.success("✅ PDF erfolgreich erstellt!")
    with open(pfad, "rb") as f:
        st.download_button("📥 PDF herunterladen", f, file_name="Zahlungsplan.pdf", mime="application/pdf")
