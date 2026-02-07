import stripe
import streamlit as st
import os

# API Key Streamlit Secrets se load ho rahi hai
stripe.api_key = st.secrets["STRIPE_SECRET_KEY"]

# Aapka Real Streamlit URL
BASE_URL = "https://compliancebotai.streamlit.app"

def create_stripe_checkout(price_id, user_email):
    """
    Stripe Checkout Session create karta hai aur redirect URL return karta hai.
    Success URL mein Checkout Session ID attach ki gayi hai.
    """
    try:
        session = stripe.checkout.Session.create(
            mode="subscription",
            payment_method_types=["card"],
            customer_email=user_email,
            line_items=[{
                "price": price_id,
                "quantity": 1
            }],
            # success_url mein {CHECKOUT_SESSION_ID} Stripe automatically replace kar dega
            success_url=f"{BASE_URL}/?payment=success&session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{BASE_URL}/?payment=cancel",
        )
        return session.url
    except Exception as e:
        return f"Error: {str(e)}"
