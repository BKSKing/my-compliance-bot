import streamlit as st
import json
import pandas as pd
import os  # <--- Added
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

# ---------------- CLIENT INITIALIZATION ----------------
# Sidebar se key wala part hata diya, ab seedha os.getenv use hoga
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# ---------------- SIDEBAR ----------------
st.sidebar.markdown("### Plans")
st.sidebar.markdown("""
Free – Limited scans   
Professional – Compliance reports   
Enterprise – Audit & ERP integration   
""")

# ---------------- FUNCTIONS ----------------
def extract_json_safely(text):
    try:
        clean_text = text.replace("```json", "").replace("```", "").strip()
        start = clean_text.find("{")
        end = clean_text.rfind("}") + 1
        if start == -1 or end == -1:
            return None
        return json.loads(clean_text[start:end])
    except Exception as e:
        print(f"JSON Error: {e}")
        return None

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
# API Key check from Environment Variable
if not os.getenv("GROQ_API_KEY"):
    st.error("❌ API Key Not Found! Please set 'GROQ_API_KEY' in your environment variables.")
    st.stop()

uploaded_file = st.file_uploader("Upload Invoice (PDF)", type="pdf")

if uploaded_file:
    with st.spinner("Extracting text from document..."):
        invoice_text = extract_text_from_pdf(uploaded_file)
    
    st.success("Document processed successfully.")

    if st.button("Analyze Compliance"):
        with st.spinner("Performing regulatory analysis..."):
            
            prompt = f"""
            Analyze the following invoice strictly from a global regulatory perspective.
            Identify ALL compliance violations across taxation, invoicing, trade, and statutory requirements.

            Return output strictly as a JSON object with this structure:
            {{
              "violations": [
                {{
                  "violation": "Short description",
                  "law_reference": "Specific law section",
                  "financial_exposure": "Monetary penalty amount",
                  "liable_entity": "Who is responsible",
                  "credit_or_deduction_impact": "Impact on tax credits",
                  "risk_level": "LOW | MEDIUM | HIGH",
                  "regulatory_notice_probability_percent": "e.g. 85%"
                }}
              ],
              "notice_reply_draft": "Professional legal response draft..."
            }}

            Invoice Text:
            {invoice_text}
            """

            try:
                completion = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[{"role": "user", "content": prompt}],
                )

                raw_content = completion.choices[0].message.content
                json_data = extract_json_safely(raw_content)

                if json_data and "violations" in json_data:
                    df = pd.DataFrame(json_data["violations"])
                    notice_draft = json_data.get("notice_reply_draft", "No draft generated.")

                    st.success("Compliance analysis completed.")
                    
                    st.subheader("Identified Compliance Violations")
                    st.dataframe(df, use_container_width=True)

                    try:
                        probs = df["regulatory_notice_probability_percent"].astype(str).str.replace("%", "")
                        avg_risk = pd.to_numeric(probs, errors='coerce').fillna(0).mean()
                        st.metric("Overall Regulatory Notice Probability", f"{round(avg_risk, 1)}%")
                    except:
                        st.metric("Overall Regulatory Notice Probability", "N/A")

                    st.subheader("Draft Regulatory Response")
                    st.text_area("Auto-generated Notice Reply", notice_draft, height=250)

                    pdf_file = generate_compliance_pdf(df, notice_draft)
                    with open(pdf_file, "rb") as f:
                        st.download_button(
                            label="Download Compliance Report (PDF)",
                            data=f,
                            file_name="Compliance_Audit_Report.pdf",
                            mime="application/pdf"
                        )
                else:
                    st.error("AI output was not in the correct format. Raw output shown below:")
                    st.code(raw_content)

            except Exception as e:
                st.error(f"Analysis failed: {e}")

# ---------------- FOOTER ----------------
st.markdown("---")
st.markdown("**Disclaimer:** This software provides automated compliance insights and does not constitute legal advice.")



