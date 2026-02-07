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

# ---------------- PAGE SETUP ----------------
st.set_page_config(page_title="ComplianceBot AI", page_icon="🛡️", layout="wide")

# ✅ PAYMENT HANDLERS (STRIPE & RAZORPAY)
params = st.query_params

# 1. Stripe Handler
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
            st.error(f"Stripe Verification Error: {e}")

# 2. Razorpay Handler
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
        # Clean URL and refresh
        st.query_params.clear()
        st.rerun()
    except Exception as e:
        st.error("Razorpay payment verification failed.")

# 🚀 LANDING PAGE / LOGIN / SIGNUP
if not st.session_state.user:
    st.title("🛡️ ComplianceBot AI")
    st.markdown("**Global Compliance & Invoice Risk Detection Platform**")
    
    tab1, tab2 = st.tabs(["Login", "Signup"])
    with tab1:
        email = st.text_input("Email", key="login_email")
        password = st.text_input("Password", type="password", key="login_pass")
        if st.button("Login"):
            res = login(email, password)
            if res and hasattr(res, 'user'):
                st.session_state.user = res.user
                st.rerun()
            else:
                st.error("Invalid credentials.")
    with tab2:
        s_email = st.text_input("Email", key="sig_email")
        s_pass = st.text_input("Password", type="password", key="sig_pass")
        if st.button("Signup"):
            res = signup(s_email, s_pass)
            if res: 
                create_user(res.user.id, s_email)
                st.success("Account created! You can now login.")
    st.stop()

# 🚦 FETCH USER DATA
user_data_resp = supabase.table("users").select("*").eq(
    "email", st.session_state.user.email
).single().execute()

user_data = user_data_resp.data
plan = user_data.get("plan", "free")
scans_used = user_data.get("scans_used", 0)
user_country = user_data.get("country") or "IN"

# Sidebar for Status
st.sidebar.title("💎 Membership")
st.sidebar.write(f"User: {st.session_state.user.email}")
st.sidebar.write(f"Plan: {plan.upper()}")

if plan == "free":
    remaining = max(0, FREE_SCAN_LIMIT - scans_used)
    st.sidebar.progress(scans_used / FREE_SCAN_LIMIT)
    st.sidebar.write(f"Free Scans Left: {remaining}")
else:
    st.sidebar.success("Pro Plan: Unlimited Scans")

if st.sidebar.button("Logout"):
    st.session_state.user = None
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

# ---------------- MAIN SCANNER LOGIC ----------------
st.title("🛡️ ComplianceBot AI")
st.subheader("Global Invoice & Regulatory Compliance Scanner")

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

uploaded_file = st.file_uploader("Upload Invoice (PDF)", type="pdf")

if uploaded_file:
    invoice_text = extract_text_from_pdf(uploaded_file)
    st.success("PDF Loaded successfully.")

    if st.button("Analyze Compliance"):
        
        # 🚫 1. PAYWALL CHECK
        if plan != "pro" and scans_used >= FREE_SCAN_LIMIT:
            st.warning("🚨 Free limit reached. Upgrade to Pro to continue scanning.")
            
            pricing = get_pricing(user_country)
            st.markdown(f"### 💎 Upgrade to Pro ({pricing['currency']}{pricing['price']}/mo)")

            # STRIPE GATEWAY
            if pricing["provider"] == "stripe":
                url = create_stripe_checkout(pricing["price_id"], st.session_state.user.email)
                if url.startswith("http"):
                    st.link_button("🚀 Pay with Stripe", url)
            
            # RAZORPAY GATEWAY
            elif pricing["provider"] == "razorpay":
                if st.button("🚀 Upgrade via Razorpay (India)"):
                    order = create_razorpay_order(pricing["price"], st.session_state.user.email)
                    
                    razorpay_html = f"""
                    <script src="https://checkout.razorpay.com/v1/checkout.js"></script>
                    <script>
                    var options = {{
                        "key": "{st.secrets['RAZORPAY_KEY_ID']}",
                        "amount": "{order['amount']}",
                        "currency": "INR",
                        "name": "ComplianceBot AI",
                        "description": "Pro Subscription",
                        "order_id": "{order['id']}",
                        "handler": function (response) {{
                            window.parent.location.href = window.parent.location.origin + window.parent.location.pathname + 
                              "?razorpay_payment_id=" + response.razorpay_payment_id +
                              "&razorpay_order_id=" + response.razorpay_order_id +
                              "&razorpay_signature=" + response.razorpay_signature;
                        }},
                        "prefill": {{ "email": "{st.session_state.user.email}" }},
                        "theme": {{ "color": "#0f172a" }}
                    }};
                    var rzp = new Razorpay(options);
                    rzp.open();
                    </script>
                    """
                    components.html(razorpay_html, height=0)
            
            st.stop() 

        # 🟢 2. PROCEED WITH ANALYSIS
        with st.spinner("Analyzing with AI..."):
            prompt = f"Analyze this invoice for compliance violations. Output JSON only. Text: {invoice_text}"
            
            completion = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}]
            )
            
            json_data = extract_json_safely(completion.choices[0].message.content)

            if json_data:
                increment_scan(st.session_state.user.email)
                st.info("Analysis Complete.")
                if json_data.get("violations"):
                    df = pd.DataFrame(json_data["violations"])
                    st.dataframe(df, use_container_width=True)
                    
                    if plan == "pro":
                        pdf_path = generate_compliance_pdf(df, json_data.get("notice_reply_draft", ""), json_data.get("invoice_context", {}))
                        with open(pdf_path, "rb") as f:
                            st.download_button("Download Report PDF", f, "Audit_Report.pdf")
                    else:
                        st.info("💡 Upgrade to Pro to download the PDF report.")
                else:
                    st.success("No violations found!")
            else:
                st.error("AI Error. Please try again.")

st.markdown("---")
st.caption("© 2026 ComplianceBot AI. Not legal advice.")




