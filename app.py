import streamlit as st
from groq import Groq
from PyPDF2 import PdfReader

# Page Setup
st.set_page_config(page_title="ComplianceBot AI", page_icon="🛡️")
st.title("🛡️ ComplianceBot AI")
st.subheader("PDF Invoice Scanner (Global Compliance)")

# Sidebar for API Key
api_key = st.sidebar.text_input("Apni Groq API Key daalein:", type="password")

def extract_text_from_pdf(pdf_file):
    reader = PdfReader(pdf_file)
    text = ""
    for page in reader.pages:
        text += page.extract_text()
    return text

if api_key:
    client = Groq(api_key=api_key)
    
    # PDF Upload Option
    uploaded_file = st.file_uploader("Apna Invoice (PDF) upload karein", type="pdf")

    if uploaded_file is not None:
        with st.spinner("PDF read kiya ja raha hai..."):
            invoice_text = extract_text_from_pdf(uploaded_file)
            st.info("PDF scan ho gaya. Ab AI analyze kar raha hai...")

        if st.button("Analyze Compliance"):
            with st.spinner("AI rules check kar raha hai..."):
                prompt = f"""
                Analyze this invoice for global trade compliance:
                1. Identify potential Tax/VAT/GST risks.
                2. Check for missing mandatory fields (Tax IDs, addresses).
                3. Check for 2026 Environmental/Green Regulation (CBAM) compliance.
                
                Invoice Text: {invoice_text}
                
                Provide a Risk Score (0-10) and specific Action Steps.
                """
                
                try:
                    completion = client.chat.completions.create(
                        model="llama-3.3-70b-versatile",
                        messages=[{"role": "user", "content": prompt}],
                    )
                    st.success("Analysis Complete!")
                    st.markdown(completion.choices[0].message.content)
                except Exception as e:
                    st.error(f"Error: {e}")
else:
    st.info("Shuru karne ke liye side mein API key daalein.")
