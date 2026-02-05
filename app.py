import streamlit as st
import json
import pandas as pd
from groq import Groq
from PyPDF2 import PdfReader
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER

# ---------------- PAGE SETUP ----------------
st.set_page_config(
    page_title="ComplianceBot AI",
    page_icon="🛡️",
    layout="wide"
)

st.title("🛡️ ComplianceBot AI")
st.subheader("Global Invoice & Regulatory Compliance Scanner")

# ---------------- SIDEBAR ----------------
api_key = st.sidebar.text_input("API Key", type="password")

st.sidebar.markdown("### Plans")
st.sidebar.markdown("""
Free – Limited scans  
Professional – Compliance reports  
Enterprise – Audit & ERP integration  
""")

# ---------------- FUNCTIONS ----------------
def extract_text_from_pdf(pdf_file):
    reader = PdfReader(pdf_file)
    text = ""
    for page in reader.pages:
        if page.extract_text():
            text += page.extract_text()
    return text


def generate_compliance_pdf(df, notice_draft):
    file_path = "Compliance_Audit_Report.pdf"
    doc = SimpleDocTemplate(file_path)
    styles = getSampleStyleSheet()

    header_style = ParagraphStyle(
        "Header",
        parent=styles["Title"],
        alignment=TA_CENTER
    )

    elements = []

    elements.append(Paragraph("COMPLIANCE AUDIT REPORT", header_style))
    elements.append(Spacer(1, 12))
    elements.append(Paragraph("Issued by ComplianceBot AI", styles["Normal"]))
    elements.append(Paragraph("Automated Regulatory Risk Assessment", styles["Italic"]))
    elements.append(Spacer(1, 20))

    elements.append(Paragraph("<b>Identified Compliance Issues</b>", styles["Heading2"]))
    elements.append(Spacer(1, 10))

    table_data = [df.columns.tolist()] + df.values.tolist()
    table = Table(table_data, repeatRows=1)
    elements.append(table)

    elements.append(Spacer(1, 20))
    elements.append(Paragraph("<b>Draft Response to Regulatory Authority</b>", styles["Heading2"]))
    elements.append(Spacer(1, 10))
    elements.append(Paragraph(notice_draft.replace("\n", "<br/>"), styles["Normal"]))

    doc.build(elements)
    return file_path


# ---------------- MAIN ----------------
if not api_key:
    st.info("Please enter your API key to begin.")
    st.stop()

client = Groq(api_key=api_key)

uploaded_file = st.file_uploader("Upload Invoice (PDF)", type="pdf")

if uploaded_file:
    with st.spinner("Extracting text from document..."):
        invoice_text = extract_text_from_pdf(uploaded_file)

    st.success("Document processed successfully.")

    if st.button("Analyze Compliance"):
        with st.spinner("Performing regulatory analysis..."):

            prompt = f"""
You are a senior global compliance auditor working with tax authorities,
customs departments, and regulatory bodies.

Analyze the following invoice strictly from a global regulatory perspective.

Identify ALL compliance violations across taxation, invoicing, trade,
and statutory disclosure requirements.

For EACH violation, return output strictly as a JSON ARRAY:

[
  {{
    "violation": "",
    "law_reference": "",
    "financial_exposure": "",
    "liable_entity": "",
    "credit_or_deduction_impact": "",
    "risk_level": "LOW | MEDIUM | HIGH",
    "regulatory_notice_probability_percent": ""
  }}
]

Then also generate a separate section called "NOTICE_REPLY_DRAFT"
written in professional legal language, suitable for submission
to a tax authority or regulatory body.

Invoice Text:
{invoice_text}

Rules:
- Use neutral global legal language
- Mention law sections where applicable
- Financial exposure must be monetary
- Probability must be numeric %
- Return STRICT JSON in this structure:

{{
  "violations": [...],
  "notice_reply_draft": "..."
}}
"""

            try:
                completion = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[{"role": "user", "content": prompt}],
                )

                result = json.loads(completion.choices[0].message.content)

                df = pd.DataFrame(result["violations"])
                notice_draft = result["notice_reply_draft"]

                st.success("Compliance analysis completed.")

                st.subheader("Identified Compliance Violations")
                st.dataframe(df, use_container_width=True)

                avg_risk = (
                    df["regulatory_notice_probability_percent"]
                    .astype(str)
                    .str.replace("%", "")
                    .astype(float)
                    .mean()
                )

                st.metric(
                    "Overall Regulatory Notice Probability",
                    f"{round(avg_risk, 1)}%"
                )

                st.subheader("Draft Regulatory Response")
                st.text_area(
                    "Auto-generated Notice Reply",
                    notice_draft,
                    height=250
                )

                if st.button("Download Compliance Report (PDF)"):
                    pdf = generate_compliance_pdf(df, notice_draft)
                    with open(pdf, "rb") as f:
                        st.download_button(
                            "Download PDF",
                            f,
                            file_name="Compliance_Audit_Report.pdf",
                            mime="application/pdf"
                        )

            except Exception as e:
                st.error("Analysis failed.")
                st.code(str(e))

# ---------------- FOOTER ----------------
st.markdown("---")
st.markdown(
    "**Disclaimer:** This software provides automated compliance insights and does not constitute legal advice."
)

