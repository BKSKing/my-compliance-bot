import stripe
import streamlit as st

stripe.api_key = st.secrets["STRIPE_SECRET_KEY"]

def create_stripe_checkout(price_id, user_email):
    session = stripe.checkout.Session.create(
        payment_method_types=["card"],
        mode="subscription",
        customer_email=user_email,
        line_items=[
            {
                "price": price_id,
                "quantity": 1,
            }
        ],
        success_url="https://your-app-url?success=true",
        cancel_url="https://your-app-url?cancel=true",
    )
    return session.url
