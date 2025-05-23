import streamlit as st
import pandas as pd
from fpdf import FPDF
import pdfplumber
import tempfile

def extract_text_from_pdf(file):
    with pdfplumber.open(file) as pdf:
        return "\n".join([page.extract_text() for page in pdf.pages if page.extract_text()])

def extract_amount(text):
    for line in reversed(text.split("\n")):
        if any(k in line.lower() for k in ["gesamtbetrag", "gesamt", "betrag", "total"]):
            for word in line.split():
                cleaned = word.replace(".", "").replace(",", ".").replace("€", "")
                try:
                    return round(float(cleaned), 2)
                except:
                    continue
    return 0.0

def detect_file_type(text):
    if "gastro" in text.lower() or "fettabluft" in text.lower():
        return "gastro"
    elif "werbung" in text.lower() or "marketing" in text.lower():
        return "werbung"
    else:
        return "miete"

def extract_info_fields(text):
    lines = text.split("\n")
    name, adresse, vertragsnummer = "", "", ""
    for line in lines:
        if not name and any(w in line.lower() for w in ["gmbh", "king", "burger", "dang", "bk"]):
            name = line.strip()
        if not adresse and any(c in line.lower() for c in ["straße", "str.", "allee", "platz", "weg"]):
            adresse = line.strip()
        if not vertragsnummer and any(c in line.lower() for c in ["vertrag", "vertragsnummer", "vertrags-nr"]):
            vertragsnummer = line.strip().split()[-1]
    return name, adresse, vertragsnummer

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
        row = [monat, miete, wb, gastro if gastro is not None else None]
        row.append(sum(filter(None, [miete, wb, gastro])))
        rows.append(row)
    return pd.DataFrame(rows, columns=["Monat", "Miete + Nebenkosten", "Werbebeitrag", "Gastro (Fettabluft)", "Monatlich insgesamt"])

def generate_pdf(df, mietername, adresse, vertragsnummer):
    pdf = PDF(mietername, adresse, vertragsnummer)
    pdf.add_page()

    spalten = df.columns.tolist()
    breiten = [38, 38, 38, 38, 38]

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

    lines = [
        "Zahlungsempfänger & Kontoverbindungen:",
        "",
        "1. Miete + Nebenkosten - Kontoinhaber: HBB Gewerbebau Projektgesellschaft",
        "IBAN: DE94 1003 0200 1052 5300 42 | BIC: BHYPDEB2XXX | Bank: Berlin Hyp",
        f"Verwendungszweck: {vertragsnummer}",
        "",
        "2. Werbebeiträge - Kontoinhaber: HBB Centermanagement GmbH & Co. KG",
        "IBAN: DE39 2005 0550 1002 2985 84 | BIC: HASPDEHHXXX | Bank: Hamburger Sparkasse",
        f"Verwendungszweck: {vertragsnummer}"
    ]
    if df["Gastro (Fettabluft)"].notna().any():
        lines += [
            "",
            "3. Gastro - Kontoinhaber: HBB Betreuungsgesellschaft mbH",
            "IBAN: DE56 2005 0550 1002 2562 77 | BIC: HASPDEHHXXX | Bank: Hamburger Sparkasse"
        ]
    for line in lines:
        pdf.multi_cell(180, 6, line, align="L")

    temp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    pdf.output(temp.name)
    return temp.name

# Streamlit UI
st.set_page_config(page_title="Zahlungsplan Generator")
st.title("📄 Zahlungsplan Generator")

mietername = ""
adresse = ""
vertragsnummer = ""
miete = werbung = gastro = 0.0

uploaded_files = st.file_uploader("PDF-Rechnungen hochladen", type="pdf", accept_multiple_files=True)

if uploaded_files:
    for file in uploaded_files:
        text = extract_text_from_pdf(file)
        betrag = extract_amount(text)
        typ = detect_file_type(text)
        name, addr, vertrag = extract_info_fields(text)

        if name: mietername = name
        if addr: adresse = addr
        if vertrag: vertragsnummer = vertrag

        if typ == "miete": miete = betrag
        elif typ == "werbung": werbung = betrag
        elif typ == "gastro": gastro = betrag

mietername = st.text_input("Mietername", value=mietername)
adresse = st.text_input("Adresse", value=adresse)
vertragsnummer = st.text_input("Vertragsnummer", value=vertragsnummer)
miete = st.number_input("Miete + Nebenkosten", value=miete, step=0.01)
werbung = st.number_input("Werbebeitrag (halbjährlich)", value=werbung, step=0.01)
gastro = st.number_input("Gastro (monatlich)", value=gastro, step=0.01)

if st.button("PDF erzeugen"):
    df = create_payment_plan(miete, werbung, gastro)
    pfad = generate_pdf(df, mietername, adresse, vertragsnummer)
    st.success("✅ PDF wurde erstellt")
    with open(pfad, "rb") as f:
        st.download_button("📥 PDF herunterladen", f, file_name="Zahlungsplan.pdf", mime="application/pdf")