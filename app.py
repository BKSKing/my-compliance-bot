import streamlit as st
from groq import Groq

# Page Setup
st.set_page_config(page_title="ComplianceBot AI", page_icon="🛡️")
st.title("🛡️ ComplianceBot AI")
st.subheader("International Tax & Compliance Scanner")

# Sidebar for API Key
api_key = st.sidebar.text_input("Apni Groq API Key yahan daalein:", type="password")

if api_key:
    client = Groq(api_key=api_key)
    
    # Input Area
    invoice_text = st.text_area("Invoice ka text yahan paste karein:", placeholder="E.g. Invoice #123, Amount $5000, From India to Germany...", height=200)

    if st.button("Scan for Risks"):
        if invoice_text:
            with st.spinner("AI rules check kar raha hai..."):
                prompt = f"""
                You are a Global Trade Compliance Expert. 
                Analyze this invoice text and identify:
                1. Potential Tax Violations (VAT/GST/Digital Tax).
                2. Missing Mandatory Information (Tax ID, Address, etc.).
                3. Environmental/Green Regulation risks (2026 standards like CBAM).
                
                Invoice Text: {invoice_text}
                
                Provide a simple 'Risk Score' (0-10) and 'Action Steps' in bullet points.
                """
                
                try:
                    completion = client.chat.completions.create(
                        model="llama-3.3-70b-versatile",
                        messages=[{"role": "user", "content": prompt}],
                    )
                    
                    # Display Results
                    st.success("Analysis Complete!")
                    st.markdown(completion.choices[0].message.content)
                except Exception as e:
                    st.error(f"Error: {e}")
        else:
            st.warning("Please enter some text to scan.")
else:
    st.info("Side mein apni API key daalein shuru karne ke liye.")
