import razorpay
import streamlit as st

client = razorpay.Client(
    auth=(
        st.secrets["RAZORPAY_KEY_ID"],
        st.secrets["RAZORPAY_KEY_SECRET"]
    )
)

def create_razorpay_order(amount_inr, user_email):
    order = client.order.create({
        "amount": int(amount_inr * 100),  # ₹ → paise
        "currency": "INR",
        "payment_capture": 1,
        "notes": {
            "email": user_email,
            "plan": "pro"
        }
    })
    return order
