import streamlit as st
import stripe
import json
import pandas as pd
import os
import streamlit.components.v1 as components
from groq import Groq
from PyPDF2 import PdfReader
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch

# 🔹 FIXED IMPORTS
from auth import signup, login
from db import (
    supabase,
    get_user,
    create_user,
    increment_scan,
    update_user_to_pro
)
from pricing import get_pricing
from payments.stripe_client import create_stripe_checkout
from razorpay_client import client as razorpay_client, create_razorpay_order

# --- CONFIGURATION ---
FREE_SCAN_LIMIT = 3
stripe.api_key = st.secrets["STRIPE_SECRET_KEY"]

if "user" not in st.session_state:
    st.session_state.user = None

# ---------------- PAGE SETUP ----------------
st.set_page_config(page_title="ComplianceBot AI", page_icon="🛡️", layout="wide")

# ✅ PAYMENT HANDLERS (Stripe & Razorpay Verification)
params = st.query_params

# Stripe Verification
if params.get("payment") == "success":
    session_id = params.get("session_id")
    if session_id:
        try:
            session = stripe.checkout.Session.retrieve(session_id)
            if session.payment_status == "paid":
                update_user_to_pro(session.customer_email)
                st.success("🎉 Stripe Payment successful! Pro activated.")
                st.balloons()
        except Exception as e:
            st.error(f"Stripe Error: {e}")

# Razorpay Verification
if "razorpay_payment_id" in params:
    try:
        razorpay_client.utility.verify_payment_signature({
            "razorpay_order_id": params["razorpay_order_id"],
            "razorpay_payment_id": params["razorpay_payment_id"],
            "razorpay_signature": params["razorpay_signature"],
        })
        update_user_to_pro(st.session_state.user.email)
        st.success("🎉 Razorpay Payment successful! Pro activated.")
        st.balloons()
        st.query_params.clear()
        st.rerun()
    except:
        st.error("Razorpay verification failed.")

# ---------------- HELPER FUNCTIONS ----------------

def calculate_risk_summary(df):
    high = sum(df["risk_level"].str.upper() == "HIGH")
    medium = sum(df["risk_level"].str.upper() == "MEDIUM")
    low = sum(df["risk_level"].str.upper() == "LOW")
    total = max(1, high + medium + low)
    score = int(((high * 3) + (medium * 2) + (low * 1)) / (total * 3) * 100)
    return {"HIGH": high, "MEDIUM": medium, "LOW": low, "SCORE": score}

def generate_compliance_pdf(df, notice_draft, context):
    file_path = "Compliance_Audit_Report.pdf"
    doc = SimpleDocTemplate(file_path, pagesize=A4, rightMargin=40, leftMargin=40, topMargin=50, bottomMargin=40)
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="CoverTitle", fontSize=22, spaceAfter=20, alignment=TA_CENTER, fontName="Helvetica-Bold"))
    styles.add(ParagraphStyle(name="SectionHeader", fontSize=14, spaceBefore=20, spaceAfter=10, fontName="Helvetica-Bold", textColor=colors.black))
    styles.add(ParagraphStyle(name="Body", fontSize=10, spaceAfter=8, leading=12))

    elements = []
    risk = calculate_risk_summary(df)

    elements.append(Spacer(1, 2 * inch))
    elements.append(Paragraph("GLOBAL COMPLIANCE RISK ASSESSMENT REPORT", styles["CoverTitle"]))
    elements.append(Spacer(1, 0.5 * inch))
    elements.append(Paragraph(f"<b>Prepared for:</b> {st.session_state.user.email}<br/>"
                              "<b>Prepared by:</b> ComplianceBot AI (Independent Auditor)<br/>"
                              "<b>Classification:</b> Confidential & Privileged", styles["Body"]))
    elements.append(Spacer(1, 2 * inch))

    elements.append(Paragraph("Board-Level Executive Summary", styles["SectionHeader"]))
    elements.append(Paragraph(f"""
        This independent assessment identifies material regulatory risks for a <b>{context.get('transaction_type')}</b> transaction.
        <br/><br/><b>Key Findings:</b>
        <ul>
            <li>Total Issues Identified: {len(df)}</li>
            <li>High-Risk Exposures: {risk['HIGH']}</li>
            <li>Regulatory Scrutiny Probability: {risk['SCORE']}%</li>
        </ul>
        <b>Recommendation:</b> Immediate corrective action is required prior to audit submission.
    """, styles["Body"]))

    elements.append(Paragraph("Compliance Risk Heat-Map", styles["SectionHeader"]))
    heatmap_data = [["Risk Category", "Incident Count"], ["Critical (High)", risk["HIGH"]], ["Warning (Medium)", risk["MEDIUM"]], ["Advisory (Low)", risk["LOW"]], ["Weighted Risk Score", f"{risk['SCORE']}%"]]
    heatmap_table = Table(heatmap_data, colWidths=[2 * inch, 1.5 * inch])
    heatmap_table.setStyle([('GRID', (0,0), (-1,-1), 0.5, colors.grey), ('BACKGROUND', (0,1), (1,1), colors.red), ('BACKGROUND', (0,2), (1,2), colors.orange), ('BACKGROUND', (0,3), (1,3), colors.lightgreen), ('FONT', (0,0), (-1,0), 'Helvetica-Bold')])
    elements.append(heatmap_table)

    elements.append(Paragraph("Detailed Statutory Violations", styles["SectionHeader"]))
    table_data = [["Violation", "Evidence", "Law Ref", "Risk"]] + df[["violation", "evidence_from_invoice", "law_reference", "risk_level"]].values.tolist()
    v_table = Table(table_data, repeatRows=1, colWidths=[1.2*inch, 1.8*inch, 1.5*inch, 0.6*inch])
    v_table.setStyle([('GRID', (0,0), (-1,-1), 0.5, colors.grey), ('FONTSIZE', (0,0), (-1,-1), 7), ('BACKGROUND', (0,0), (-1,0), colors.whitesmoke)])
    elements.append(v_table)

    elements.append(Paragraph("Draft Regulatory Response (Legal Defense)", styles["SectionHeader"]))
    elements.append(Paragraph(notice_draft.replace("\n", "<br/>"), styles["Body"]))

    doc.build(elements)
    return file_path

def extract_json_safely(text):
    try:
        clean_text = text.replace("```json", "").replace("```", "").strip()
        start, end = clean_text.find("{"), clean_text.rfind("}") + 1
        return json.loads(clean_text[start:end])
    except: return None

def extract_text_from_pdf(pdf_file):
    reader = PdfReader(pdf_file)
    return "".join([page.extract_text() for page in reader.pages if page.extract_text()])

# ---------------- LOGIN / AUTH ----------------
if not st.session_state.user:
    st.title("🛡️ ComplianceBot AI")
    tab1, tab2 = st.tabs(["Login", "Signup"])
    with tab1:
        email = st.text_input("Email", key="login_email")
        password = st.text_input("Password", type="password", key="login_pass")
        if st.button("Login"):
            res = login(email, password)
            if res and hasattr(res, 'user'):
                st.session_state.user = res.user
                st.rerun()
    with tab2:
        s_email = st.text_input("Email", key="sig_email")
        s_pass = st.text_input("Password", type="password", key="sig_pass")
        if st.button("Signup"):
            res = signup(s_email, s_pass)
            if res: 
                create_user(res.user.id, s_email)
                st.success("Account created! Login now.")
    st.stop()

# 🚦 DATA FETCH
user_data_resp = supabase.table("users").select("*").eq("email", st.session_state.user.email).single().execute()
user_data = user_data_resp.data
plan = user_data.get("plan", "free")
scans_used = user_data.get("scans_used", 0)
user_country = user_data.get("country") or "IN"

# 💎 SIDEBAR
st.sidebar.title("💎 Membership")
st.sidebar.write(f"User: **{st.session_state.user.email}**")
st.sidebar.write(f"Plan: **{plan.upper()}**")
if plan == "free":
    remaining = max(0, FREE_SCAN_LIMIT - scans_used)
    st.sidebar.progress(min(1.0, scans_used / FREE_SCAN_LIMIT))
    st.sidebar.write(f"Free Scans Left: {remaining} / {FREE_SCAN_LIMIT}")
if st.sidebar.button("Logout"):
    st.session_state.clear()
    st.rerun()

# ---------------- MAIN APP ----------------
st.title("🛡️ ComplianceBot AI")
client = Groq(api_key=os.getenv("GROQ_API_KEY"))
uploaded_file = st.file_uploader("Upload Invoice (PDF)", type="pdf")

if uploaded_file:
    invoice_text = extract_text_from_pdf(uploaded_file)
    
    # 🚨 PAYMENT GATING (Razorpay & Stripe Buttons)
    if plan != "pro" and scans_used >= FREE_SCAN_LIMIT:
        st.error("🚨 Free limit reached!")
        pricing = get_pricing(user_country)
        
        # Stripe Option
        if pricing["provider"] == "stripe":
            st.link_button("🚀 Upgrade via Stripe", create_stripe_checkout(pricing["price_id"], st.session_state.user.email))
        
        # Razorpay Option (FIXED: Added Back)
        elif pricing["provider"] == "razorpay":
            if st.button("🚀 Pay & Upgrade with Razorpay"):
                with st.spinner("Opening Secure Payment Gateway..."):
                    order = create_razorpay_order(pricing["price"], st.session_state.user.email)
                    if order:
                        razorpay_js = f"""
                        <script src="https://checkout.razorpay.com/v1/checkout.js"></script>
                        <script>
                            var options = {{
                                "key": "{st.secrets['RAZORPAY_KEY_ID']}",
                                "amount": "{order['amount']}",
                                "currency": "INR",
                                "name": "ComplianceBot AI",
                                "description": "Upgrade to Pro",
                                "order_id": "{order['id']}",
                                "handler": function (response) {{
                                    var url = window.parent.location.origin + window.parent.location.pathname + 
                                      "?razorpay_payment_id=" + response.razorpay_payment_id +
                                      "&razorpay_order_id=" + response.razorpay_order_id +
                                      "&razorpay_signature=" + response.razorpay_signature;
                                    window.parent.location.href = url;
                                }},
                                "prefill": {{ "email": "{st.session_state.user.email}" }},
                                "theme": {{ "color": "#0f172a" }}
                            }};
                            var rzp = new Razorpay(options);
                            rzp.open();
                        </script>
                        """
                        components.html(razorpay_js, height=600)
        st.stop()

    if st.button("Analyze Compliance"):
        with st.spinner("Senior Auditor is conducting forensic review..."):
            # 🔥 PROMPT (UNCHANGED as requested)
            prompt = f"""
            You are a Tier-1 Global Compliance Auditor (McKinsey/Big-4). 
            Perform a legally defensible, forensic audit of the provided invoice.

            STEP 1 — JURISDICTION MAPPING:
            Extract Seller/Buyer Country, Transaction Type (Domestic/Cross-border), and Nature of Supply.

            STEP 2 — MANDATORY LEGAL AUDIT:
            Verify: Supplier/Buyer IDs, Tax Rates, Date, Invoice #, Place of Supply, Reverse Charge/Zero-Rated mentions, Currency compliance.

            STEP 3 — VIOLATION TABLE:
            Identify EVERY breach with: Violation Title, Quoted Evidence, Law Reference (Act/Section), Risk Level (Low/Med/High), Financial Exposure ($), and Probability of Notice (%).

            STEP 4 — DEFENSIVE LEGAL REPLY:
            Draft a formal, lawyer-grade response to a Tax Authority/Regulator regarding these discrepancies.

            OUTPUT STRICT JSON ONLY:
            {{
              "invoice_context": {{ "seller_country": "", "buyer_country": "", "transaction_type": "", "nature_of_supply": "" }},
              "violations": [
                {{ "violation": "", "evidence_from_invoice": "", "law_reference": "", "risk_level": "HIGH", "financial_exposure": "", "regulatory_notice_probability_percent": "" }}
              ],
              "notice_reply_draft": ""
            }}
            Invoice Text: {invoice_text}
            """

            completion = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=[{"role": "user", "content": prompt}])
            json_data = extract_json_safely(completion.choices[0].message.content)

            if json_data:
                supabase.table("scans").insert({
                    "user_email": str(st.session_state.user.email),
                    "transaction_type": str(json_data.get("invoice_context", {}).get("transaction_type", "Unknown")),
                    "violation_count": int(len(json_data.get("violations", []))),
                    "risk_score": str("High" if any(v.get('risk_level', '').upper() == 'HIGH' for v in json_data.get('violations', [])) else "Low")
                }).execute()
                increment_scan(st.session_state.user.email)
                
                st.success("Audit Complete.")
                df = pd.DataFrame(json_data["violations"])
                st.dataframe(df, use_container_width=True)
                
                pdf_file = generate_compliance_pdf(df, json_data["notice_reply_draft"], json_data["invoice_context"])
                with open(pdf_file, "rb") as f:
                    st.download_button("📂 Download McKinsey-Style Audit Report", f, file_name=pdf_file)

# --- 📜 HISTORY ---
st.markdown("---")
st.subheader("📜 Your Scan History")
history_resp = supabase.table("scans").select("*").eq("user_email", st.session_state.user.email).order("created_at", desc=True).limit(5).execute()
if history_resp.data:
    for scan in history_resp.data:
        st.write(f"📅 {scan['created_at'][:10]} | {scan['transaction_type']} | Risk: {scan['risk_score']}")
else:
    st.info("No previous scans.")

st.caption("© 2026 ComplianceBot AI. Not legal advice.")




