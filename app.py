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
if "open_razorpay" not in st.session_state:
    st.session_state.open_razorpay = False

# ---------------- PAGE SETUP ----------------
st.set_page_config(page_title="ComplianceBot AI", page_icon="🛡️", layout="wide")

# ✅ PAYMENT HANDLERS
params = st.query_params

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

# 🚀 LOGIN/SIGNUP LOGIC
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
if st.session_state.user:
    st.sidebar.write(f"User: **{st.session_state.user.email}**")
st.sidebar.write(f"Plan: **{plan.upper()}**")

if plan == "free":
    remaining = max(0, FREE_SCAN_LIMIT - scans_used)
    progress_val = min(1.0, scans_used / FREE_SCAN_LIMIT)
    st.sidebar.progress(progress_val)
    st.sidebar.write(f"Free Scans Left: {remaining} / {FREE_SCAN_LIMIT}")
else:
    st.sidebar.success("Pro Plan: Unlimited Scans")

if st.sidebar.button("Logout"):
    st.session_state.clear()
    st.rerun()

# ---------------- FUNCTIONS ----------------
def extract_json_safely(text):
    try:
        clean_text = text.replace("```json", "").replace("```", "").strip()
        start, end = clean_text.find("{"), clean_text.rfind("}") + 1
        return json.loads(clean_text[start:end])
    except: return None

def extract_text_from_pdf(pdf_file):
    reader = PdfReader(pdf_file)
    return "".join([page.extract_text() for page in reader.pages if page.extract_text()])

def generate_compliance_pdf(df, notice_draft, context):
    file_path = "Compliance_Audit_Report.pdf"
    doc = SimpleDocTemplate(file_path)
    styles = getSampleStyleSheet()
    elements = [Paragraph("COMPLIANCE AUDIT REPORT", styles["Title"]), Spacer(1, 12)]
    elements.append(Paragraph(f"Context: {context.get('transaction_type')}", styles["Normal"]))
    table_data = [df.columns.tolist()] + df.values.tolist()
    elements.append(Table(table_data))
    elements.append(Paragraph("Draft Response:", styles["Heading2"]))
    elements.append(Paragraph(notice_draft.replace("\n", "<br/>"), styles["Normal"]))
    doc.build(elements)
    return file_path

# ---------------- MAIN APP ----------------
st.title("🛡️ ComplianceBot AI")
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

uploaded_file = st.file_uploader("Upload Invoice (PDF)", type="pdf")

if uploaded_file:
    invoice_text = extract_text_from_pdf(uploaded_file)
    
    if st.button("Analyze Compliance"):
        if plan != "pro" and scans_used >= FREE_SCAN_LIMIT:
            st.warning("🚨 Free limit reached. Upgrade to Pro.")
            pricing = get_pricing(user_country)
            if pricing["provider"] == "stripe":
                url = create_stripe_checkout(pricing["price_id"], st.session_state.user.email)
                st.link_button("🚀 Upgrade via Stripe", url)
            elif pricing["provider"] == "razorpay":
                if st.button("🚀 Upgrade via Razorpay"):
                    st.session_state.open_razorpay = True
                if st.session_state.open_razorpay:
                    order = create_razorpay_order(pricing["price"], st.session_state.user.email)
                    razorpay_html = f"""
                    <script src="https://checkout.razorpay.com/v1/checkout.js"></script>
                    <script>
                        var options = {{
                            "key": "{st.secrets['RAZORPAY_KEY_ID']}",
                            "amount": "{order['amount']}",
                            "currency": "INR",
                            "name": "ComplianceBot AI",
                            "order_id": "{order['id']}",
                            "handler": function (response) {{
                                window.location.href = window.location.origin + window.location.pathname + 
                                  "?razorpay_payment_id=" + response.razorpay_payment_id +
                                  "&razorpay_order_id=" + response.razorpay_order_id +
                                  "&razorpay_signature=" + response.razorpay_signature;
                            }},
                            "prefill": {{ "email": "{st.session_state.user.email}" }},
                            "theme": {{ "color": "#0f172a" }}
                        }};
                        var rzp = new Razorpay(options);rzp.open();
                    </script>
                    """
                    components.html(razorpay_html, height=400)
                    st.session_state.open_razorpay = False
            st.stop()

        with st.spinner("Senior Auditor is reviewing your invoice..."):
            # PROMPT (Untouched)
            prompt = f"""
            You are a senior global compliance auditor specialized in VAT, GST, and international trade laws.
            Analyze the invoice text below and identify strict compliance violations.

            -------------------------
            STEP 1: CONTEXT DETERMINATION
            Extract: Seller country, Buyer country, Transaction type (Domestic/Cross-border).
            Apply laws strictly based on this jurisdiction.

            -------------------------
            STEP 2: VIOLATION CHECKLIST
            Identify ONLY real issues:
            - Missing/Invalid VAT/GST/Tax IDs.
            - Incorrect tax rates for the jurisdiction.
            - Missing "Reverse Charge" or "Zero-Rated" mentions for cross-border B2B SaaS.
            - Missing mandatory fields (Date, Unique Invoice #, Supplier Address).
            - Currency/Exchange rate compliance issues.

            -------------------------
            STEP 3: RISK & RESPONSE
            Assign Risk (Low/Med/High) and write a formal draft response for the regulator.

            OUTPUT STRICT JSON ONLY:
            {{
              "invoice_context": {{ "seller_country": "", "buyer_country": "", "transaction_type": "" }},
              "violations": [
                {{ "violation": "", "evidence_from_invoice": "", "law_reference": "", "risk_level": "", "financial_exposure": "", "regulatory_notice_probability_percent": "" }}
              ],
              "notice_reply_draft": ""
            }}

            Invoice Text: {invoice_text}
            """

            completion = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=[{"role": "user", "content": prompt}])
            json_data = extract_json_safely(completion.choices[0].message.content)

            if json_data:
                # Save scan details to DB for history
                supabase.table("scans").insert({
                    "user_email": st.session_state.user.email,
                    "transaction_type": json_data.get("invoice_context", {}).get("transaction_type"),
                    "violation_count": len(json_data.get("violations", [])),
                    "risk_score": "High" if any(v['risk_level'] == 'HIGH' for v in json_data.get('violations', [])) else "Low"
                }).execute()
                
                increment_scan(st.session_state.user.email)
                st.rerun()

# --- 📜 SCAN HISTORY SECTION ---
st.markdown("---")
st.subheader("📜 Your Scan History")

history_resp = supabase.table("scans").select("*").eq("user_email", st.session_state.user.email).order("created_at", desc=True).limit(10).execute()

if history_resp.data:
    history_df = pd.DataFrame(history_resp.data)
    # Cleaning table for display
    display_df = history_df[['created_at', 'transaction_type', 'violation_count', 'risk_score']]
    display_df.columns = ['Date', 'Type', 'Violations Found', 'Risk Level']
    st.table(display_df)
else:
    st.info("No previous scans found. Start by uploading an invoice!")

st.caption("© 2026 ComplianceBot AI. Not legal advice.")




