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
if not st.session_state.user:
    st.title("🛡️ ComplianceBot AI")
    st.subheader("Login / Signup")

    email = st.text_input("Email", key="email")
    password = st.text_input("Password (min 6 chars)", type="password", key="password")

    col1, col2 = st.columns(2)

    if col1.button("Login"):
        res = login(email, password)
        if isinstance(res, dict) and "error" in res:
            st.error("Login failed. Check email/password or email confirmation.")
            st.code(res["error"])
        elif res and res.user:
            st.session_state.user = res.user
            st.success("Login successful")
            st.rerun()
        else:
            st.error("Login failed.")

    if col2.button("Signup"):
        res = signup(email, password)
        if isinstance(res, dict) and "error" in res:
            st.error(res["error"])
        elif res and hasattr(res, 'user') and res.user:
            create_user(res.user.id, email)
            st.success("Signup successful. Please login.")
        else:
            st.error("Signup failed")

    st.stop()

# 🚦 PLAN + USAGE LIMIT LOGIC
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

def generate_compliance_pdf(df, notice_draft, context):
    file_path = "Compliance_Audit_Report.pdf"
    doc = SimpleDocTemplate(file_path)
    styles = getSampleStyleSheet()
    header_style = ParagraphStyle("Header", parent=styles["Title"], alignment=TA_CENTER)
    
    elements = []
    elements.append(Paragraph("COMPLIANCE AUDIT REPORT", header_style))
    elements.append(Spacer(1, 10))
    elements.append(Paragraph(f"<b>Detected Context:</b> {context.get('transaction_type', 'N/A')} | {context.get('currency', 'N/A')}", styles["Normal"]))
    elements.append(Spacer(1, 20))
    
    elements.append(Paragraph("<b>Identified Compliance Issues</b>", styles["Heading2"]))
    table_data = [df.columns.tolist()] + df.values.tolist()
    elements.append(Table(table_data, repeatRows=1))
    
    elements.append(Spacer(1, 20))
    elements.append(Paragraph("<b>Draft Response</b>", styles["Heading2"]))
    elements.append(Paragraph(notice_draft.replace("\n", "<br/>"), styles["Normal"]))
    
    doc.build(elements)
    return file_path

# ---------------- MAIN APP ----------------
st.title("🛡️ ComplianceBot AI")
st.subheader("Global Invoice & Regulatory Compliance Scanner")

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

uploaded_file = st.file_uploader("Upload Invoice (PDF)", type="pdf")

if uploaded_file:
    with st.spinner("Extracting text..."):
        invoice_text = extract_text_from_pdf(uploaded_file)
    st.success("Document processed successfully.")

    if st.button("Analyze Compliance"):
        with st.spinner("Performing regulatory analysis..."):
            
            # --- NEW SENIOR AUDITOR PROMPT INTEGRATED ---
            prompt = f"""
            You are a senior global compliance auditor with experience in taxation, invoicing regulations, and trade laws across multiple jurisdictions.

            Your task is to analyze the provided invoice and identify compliance issues ONLY where they are logically and legally applicable.

            -------------------------
            STEP 1: CONTEXT DETERMINATION (MANDATORY)
            -------------------------
            First, determine the invoice context strictly from the invoice text:
            - Seller country (if mentioned)
            - Buyer country (if mentioned)
            - Transaction type: Domestic | Cross-border export/import | Unable to determine
            ALSO determine the applicable CURRENCY based on the seller country. Use the correct local currency symbol.

            -------------------------
            STEP 2: VIOLATION IDENTIFICATION
            -------------------------
            Identify ONLY real, evidence-based compliance violations. explain WHAT in the invoice triggered the violation.

            -------------------------
            STEP 3: RISK & FINANCIAL EXPOSURE
            -------------------------
            Provide an ESTIMATED financial exposure using the correct currency symbol.
            Assign: Risk level (LOW/MEDIUM/HIGH) and Regulatory notice probability (%).

            -------------------------
            STEP 4: REGULATORY RESPONSE DRAFT
            -------------------------
            Draft a professional, neutral compliance response.

            OUTPUT FORMAT (STRICT JSON ONLY):
            {{
              "invoice_context": {{
                "seller_country": "",
                "buyer_country": "",
                "transaction_type": "",
                "currency": ""
              }},
              "violations": [
                {{
                  "violation": "",
                  "evidence_from_invoice": "",
                  "law_reference": "",
                  "financial_exposure": "",
                  "liable_entity": "",
                  "credit_or_deduction_impact": "",
                  "risk_level": "",
                  "regulatory_notice_probability_percent": ""
                }}
              ],
              "notice_reply_draft": ""
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

                if json_data:
                    increment_scan(user_email)
                    
                    # UI display for Context
                    ctx = json_data.get("invoice_context", {})
                    st.info(f"📍 **Context Detected:** {ctx.get('transaction_type')} | Seller: {ctx.get('seller_country')} | Currency: {ctx.get('currency')}")
                    
                    if "violations" in json_data and json_data["violations"]:
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

                        pdf_file = generate_compliance_pdf(df, notice_draft, ctx)
                        with open(pdf_file, "rb") as f:
                            st.download_button("Download PDF Report", f, "Audit_Report.pdf", "application/pdf")
                    else:
                        st.balloons()
                        st.success("No compliance violations found for this jurisdiction!")
                else:
                    st.error("AI output error. Please check the document or try again.")
            except Exception as e:
                st.error(f"Analysis failed: {e}")

st.markdown("---")
st.markdown("**Disclaimer:** Automated insights only. Not legal advice.")



