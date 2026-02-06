import streamlit as st
import json
import pandas as pd
from groq import Groq
from PyPDF2 import PdfReader
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER

# 1. PAGE SETUP & PROFESSIONAL DESIGN
st.set_page_config(page_title="ComplianceBot AI", page_icon="🛡️", layout="wide")

st.markdown("""
    <style>
    .stButton>button {
        width: 100%;
        border-radius: 10px;
        height: 3em;
        background-color: #2e76ff;
        color: white;
        font-weight: bold;
        border: none;
    }
    .stButton>button:hover { background-color: #1a56cc; }
    div[data-testid="stMetricValue"] { color: #2e76ff; }
    </style>
    """, unsafe_allow_html=True)

# 2. SESSION STATE
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'usage_count' not in st.session_state:
    st.session_state.usage_count = 0

# 3. HELPER FUNCTIONS
def extract_json_safely(text):
    try:
        clean_text = text.replace("```json", "").replace("```", "").strip()
        start = clean_text.find("{")
        end = clean_text.rfind("}") + 1
        return json.loads(clean_text[start:end]) if start != -1 else None
    except:
        return None

def extract_text_from_pdf(pdf_file):
    reader = PdfReader(pdf_file)
    return "".join([page.extract_text() for page in reader.pages if page.extract_text()])

def generate_compliance_pdf(df, notice_draft):
    file_path = "Compliance_Audit_Report.pdf"
    doc = SimpleDocTemplate(file_path)
    styles = getSampleStyleSheet()
    header_style = ParagraphStyle("Header", parent=styles["Title"], alignment=TA_CENTER)
    
    elements = [
        Paragraph("COMPLIANCE AUDIT REPORT", header_style),
        Spacer(1, 12),
        Paragraph("<b>Identified Compliance Issues</b>", styles["Heading2"]),
        Spacer(1, 10),
        Table([df.columns.tolist()] + df.values.tolist(), repeatRows=1),
        Spacer(1, 20),
        Paragraph("<b>Draft Response</b>", styles["Heading2"]),
        Paragraph(notice_draft.replace("\n", "<br/>"), styles["Normal"])
    ]
    doc.build(elements)
    return file_path

# 4. LOGIN PAGE
def show_login():
    st.title("🛡️ ComplianceBot Pro")
    st.subheader("Sign in to your Enterprise Account")
    with st.form("Login"):
        u = st.text_input("Username / Email")
        p = st.text_input("Password", type="password")
        if st.form_submit_button("Login"):
            if u == "admin" and p == "100million":
                st.session_state.logged_in = True
                st.rerun()
            else:
                st.error("Invalid Credentials")

# 5. MAIN APP LOGIC
def show_main():
    # API Key from Secrets
    try:
        api_key = st.secrets["GROQ_API_KEY"]
        client = Groq(api_key=api_key)
    except:
        st.error("Backend Error: [GROQ_API_KEY] missing in [Streamlit Secrets](https://docs.streamlit.io)!")
        return

    st.sidebar.title("💎 Membership: PRO")
    st.sidebar.write(f"Scans Used: {st.session_state.usage_count} / 2")

    if st.session_state.usage_count >= 2:
        st.sidebar.warning("🚨 FREE LIMIT REACHED")
        st.sidebar.markdown('<a href="https://rzp.io/l/your_link" target="_blank"><button style="width:100%; border-radius:10px; background-color:#ff4b4b; color:white; padding:10px; border:none; cursor:pointer;">UPGRADE TO UNLIMITED</button></a>', unsafe_allow_html=True)
    
    st.title("🛡️ ComplianceBot Audit Suite")
    uploaded_file = st.file_uploader("Upload Invoice PDF", type="pdf")

    if uploaded_file and st.session_state.usage_count < 2:
        if st.button("Start Deep Audit"):
            st.session_state.usage_count += 1
            invoice_text = extract_text_from_pdf(uploaded_file)
            
            with st.spinner("AI Auditor is checking 500+ global regulations..."):
                prompt = f"Analyze this invoice for compliance violations. Return ONLY JSON with 'violations' list and 'notice_reply_draft'. Invoice: {invoice_text}"
                
                completion = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[{"role": "user", "content": prompt}]
                )
                
                json_data = extract_json_safely(completion.choices[0].message.content)
                
                if json_data:
                    df = pd.DataFrame(json_data["violations"])
                    st.success("Audit Complete.")
                    st.dataframe(df, use_container_width=True)
                    
                    # Generate PDF
                    pdf_path = generate_compliance_pdf(df, json_data.get("notice_reply_draft", ""))
                    with open(pdf_path, "rb") as f:
                        st.download_button("Download Full Audit Report", f, file_name="Audit_Report.pdf")
                else:
                    st.error("Analysis failed to format correctly.")

# RUN
if st.session_state.logged_in:
    show_main()
else:
    show_login()


