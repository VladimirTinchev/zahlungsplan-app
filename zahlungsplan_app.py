import streamlit as st
import pandas as pd
from fpdf import FPDF
import pdfplumber
import tempfile
import os

def extract_amount_from_pdf(file):
    try:
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
    except:
        return None

def format_de_eur(value):
    try:
        if pd.isna(value) or value is None:
            return ""
        val = float(value)
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
        self.cell(0, 10, self.mietername, ln=True)
        self.set_font("Helvetica", "", 10)
        self.cell(0, 8, self.adresse, ln=True)
        self.set_font("Helvetica", "I", 10)
        self.multi_cell(0, 8, "Die Beträge sind brutto.", align="L")
        self.ln(4)

def create_payment_plan(miete, werbung, gastro):
    monate = ["Januar", "Februar", "März", "April", "Mai", "Juni", "Juli", "August", "September", "Oktober", "November", "Dezember"]
    rows = []
    for monat in monate:
        wb = werbung if monat in ["Januar", "Juli"] else None
        row = [monat, miete, None, wb, None, gastro if gastro is not None else None, None]
        row.append(sum(filter(None, [miete, wb, gastro])))
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
            format_de_eur(row.get("Gastro (Fettabluft)", None)),
            "",
            format_de_eur(row["Monatlich insgesamt"])
        ]
        for i, val in enumerate(werte):
            pdf.cell(breiten[i], 8, val, border=1, align="C")
        pdf.ln()

    pdf.ln(6)
    pdf.set_font("Helvetica", "", 9)

    konto_infos = [
        "Zahlungsempfänger & Kontoverbindungen:",
        "",
        "1. Miete + Nebenkosten - Kontoinhaber: HBB Gewerbebau Projektgesellschaft",
        "IBAN: DE94 1003 0200 1052 5300 42",
        "BIC: BHYPDEB2XXX",
        "Bank: Berlin Hyp",
        f"Verwendungszweck: {vertragsnummer}",
        "",
        "2. Werbebeiträge - Kontoinhaber: HBB Centermanagement GmbH & Co. KG",
        "IBAN: DE39 2005 0550 1002 2985 84",
        "BIC: HASPDEHHXXX",
        "Bank: Hamburger Sparkasse",
        f"Verwendungszweck: {vertragsnummer}"
    ]

    if df["Gastro (Fettabluft)"].notna().any():
        konto_infos += [
            "",
            "3. Gastro - Kontoinhaber: HBB Betreuungsgesellschaft mbH",
            "IBAN: DE56 2005 0550 1002 2562 77",
            "BIC: HASPDEHHXXX",
            "Bank: Hamburger Sparkasse"
        ]

    for line in konto_infos:
        pdf.multi_cell(180, 6, line.strip(), align="L")

    temp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    pdf.output(temp.name)
    return temp.name

# === STREAMLIT UI ===
st.set_page_config(page_title="Zahlungsplan Generator", layout="centered")
st.title("📄 Zahlungsplan Generator")

st.markdown("**Mieterinformationen**")
mietername = st.text_input("Mietername", "")
adresse = st.text_input("Adresse", "")
vertragsnummer = st.text_input("Vertragsnummer", "")

st.markdown("**📎 Lade 2 oder 3 PDF-Rechnungen hoch (Drag & Drop oder Datei auswählen):**")
uploaded_files = st.file_uploader("Rechnungen hochladen", type="pdf", accept_multiple_files=True)

if len(uploaded_files) not in [2, 3]:
    st.info("Bitte genau 2 oder 3 PDF-Dateien hochladen.")
else:
    if st.button("📑 PDF erzeugen"):
        betraege = [extract_amount_from_pdf(file) for file in uploaded_files]
        if any(b is None for b in betraege):
            st.error("Mindestens eine Datei konnte nicht gelesen werden. Bitte überprüfe die PDFs.")
        else:
            betraege.sort(reverse=True)
            miete, werbung = betraege[0], betraege[1]
            gastro = betraege[2] if len(betraege) == 3 else None

            df = create_payment_plan(miete, werbung, gastro)
            pfad = generate_pdf(df, mietername, adresse, vertragsnummer)

            st.success("✅ PDF wurde erfolgreich erstellt!")
            with open(pfad, "rb") as f:
                st.download_button("📥 PDF herunterladen", f, file_name="Zahlungsplan.pdf", mime="application/pdf")
