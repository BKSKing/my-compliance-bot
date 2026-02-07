import stripe
import os

# API Key Environment variables se load ho rahi hai
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

# Aapka Real Streamlit URL
BASE_URL = "https://compliancebotai.streamlit.app"

def create_stripe_checkout(price_id, user_email):
    """
    Stripe Checkout Session create karta hai aur redirect URL return karta hai.
    """
    try:
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
            # Real Success aur Cancel URLs
            success_url=f"{BASE_URL}/?payment=success",
            cancel_url=f"{BASE_URL}/?payment=cancel",
        )
        return session.url
    except Exception as e:
        # Agar koi error aaye toh handle karein
        return f"Error: {str(e)}"
