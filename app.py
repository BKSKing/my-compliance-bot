import streamlit as st
import json
import pandas as pd
import os
from groq import Groq
from PyPDF2 import PdfReader
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER

# 🔹 TOP of app.py: IMPORTS & SESSION STATE
from auth import signup, login
from db import get_user, create_user, increment_scan

if "user" not in st.session_state:
    st.session_state.user = None

# ---------------- PAGE SETUP ----------------
st.set_page_config(
    page_title="ComplianceBot AI",
    page_icon="🛡️",
    layout="wide"
)

# 🔐 LOGIN / SIGNUP BLOCK
# Isse PDF upload aur baaki app lock ho jayega
if not st.session_state.user:
    st.title("🛡️ ComplianceBot AI")
    st.subheader("Login / Signup to access the Audit Suite")

    email = st.text_input("Email")
    password = st.text_input("Password", type="password")

    col1, col2 = st.columns(2)

    if col1.button("Login"):
        res = login(email, password)
        # Assuming 'res' has a user object (adjust based on your auth.py)
        if res and hasattr(res, 'user') and res.user:
            st.session_state.user = res.user
            st.rerun()
        else:
            st.error("Login failed. Please check credentials.")

    if col2.button("Signup"):
        res = signup(email, password)
        if res and hasattr(res, 'user') and res.user:
            create_user(res.user.id, email)
            st.success("Signup successful. Please login.")
        else:
            st.error("Signup failed.")

    st.stop()

# 🚦 PLAN + USAGE LIMIT LOGIC (FREE vs PAID)
# Login hone ke baad user ka data fetch karte hain
user_email = st.session_state.user.email
user_data = get_user(user_email)

plan = user_data.get("plan", "free")
scans_used = user_data.get("scans_used", 0)

# Sidebar for Status
st.sidebar.title("💎 Membership")
st.sidebar.write(f"User: {user_email}")
st.sidebar.write(f"Plan: {plan.upper()}")
st.sidebar.write(f"Scans Used: {scans_used}")

if plan == "free" and scans_used >= 3:
    st.error("🚨 Free plan limit reached (3 scans). Please upgrade to Professional to continue.")
    st.sidebar.markdown("---")
    st.sidebar.button("🚀 Upgrade to Pro (₹999)")
    st.stop()

if st.sidebar.button("Logout"):
    st.session_state.user = None
    st.rerun()

# ---------------- APP LOGIC START ----------------
st.title("🛡️ ComplianceBot AI")
st.subheader("Global Invoice & Regulatory Compliance Scanner")

# Client Initialized with Hidden Key
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# ---------------- FUNCTIONS ----------------
def extract_json_safely(text):
    try:
        clean_text = text.replace("```json", "").replace("```", "").strip()
        start = clean_text.find("{")
        end = clean_text.rfind("}") + 1
        if start == -1 or end == -1: return None
        return json.loads(clean_text[start:end])
    except:
        return None

def extract_text_from_pdf(pdf_file):
    reader = PdfReader(pdf_file)
    text = ""
    for page in reader.pages:
        if page.extract_text(): text += page.extract_text()
    return text

def generate_compliance_pdf(df, notice_draft):
    file_path = "Compliance_Audit_Report.pdf"
    doc = SimpleDocTemplate(file_path)
    styles = getSampleStyleSheet()
    header_style = ParagraphStyle("Header", parent=styles["Title"], alignment=TA_CENTER)
    
    elements = []
    elements.append(Paragraph("COMPLIANCE AUDIT REPORT", header_style))
    elements.append(Spacer(1, 20))
    elements.append(Paragraph("<b>Identified Compliance Issues</b>", styles["Heading2"]))
    
    table_data = [df.columns.tolist()] + df.values.tolist()
    elements.append(Table(table_data, repeatRows=1))
    
    elements.append(Spacer(1, 20))
    elements.append(Paragraph("<b>Draft Response</b>", styles["Heading2"]))
    elements.append(Paragraph(notice_draft.replace("\n", "<br/>"), styles["Normal"]))
    
    doc.build(elements)
    return file_path

# ---------------- MAIN ----------------
uploaded_file = st.file_uploader("Upload Invoice (PDF)", type="pdf")

if uploaded_file:
    with st.spinner("Extracting text..."):
        invoice_text = extract_text_from_pdf(uploaded_file)
    st.success("Document processed successfully.")

    if st.button("Analyze Compliance"):
        with st.spinner("Performing regulatory analysis..."):
            
            # PROMPT (Unchanged)
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
                    # ✅ Increment scan count in database
                    increment_scan(user_email)
                    
                    df = pd.DataFrame(json_data["violations"])
                    notice_draft = json_data.get("notice_reply_draft", "No draft generated.")

                    st.success("Analysis Complete!")
                    st.subheader("Identified Compliance Violations")
                    st.dataframe(df, use_container_width=True)

                    # Risk Metric
                    try:
                        probs = df["regulatory_notice_probability_percent"].astype(str).str.replace("%", "")
                        avg_risk = pd.to_numeric(probs, errors='coerce').fillna(0).mean()
                        st.metric("Overall Risk Probability", f"{round(avg_risk, 1)}%")
                    except:
                        st.metric("Overall Risk Probability", "N/A")

                    st.subheader("Draft Regulatory Response")
                    st.text_area("Legal Response Draft", notice_draft, height=250)

                    pdf_file = generate_compliance_pdf(df, notice_draft)
                    with open(pdf_file, "rb") as f:
                        st.download_button("Download PDF Report", f, "Audit_Report.pdf", "application/pdf")
                else:
                    st.error("AI output error. Please try again.")
            except Exception as e:
                st.error(f"Analysis failed: {e}")

st.markdown("---")
st.markdown("**Disclaimer:** Automated insights only. Not legal advice.")



