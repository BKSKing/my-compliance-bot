# Stripe Dashboard se mile hue actual Price IDs yahan dalen
STRIPE_PRICES = {
    "US": "price_1Sy5f5QlbehJoochG6Uo5uBz",
    "EU": "price_1Sy5drQlbehJoochBzyxuFKi",
}

def get_pricing(country):
    """
    Country ke basis par currency, price, provider aur Stripe price_id return karta hai.
    """
    country = country.upper()

    # 🇮🇳 India Logic (Razorpay)
    if country == "INDIA" or country == "IN":
        return {
            "provider": "razorpay",
            "currency": "₹",
            "price": 1299,
            "price_id": None  # Razorpay usually doesn't need a static price_id like Stripe
        }

    # 🇺🇸 USA & Canada Logic (Stripe)
    elif country in ["US", "CA", "USA"]:
        return {
            "provider": "stripe",
            "currency": "$",
            "price": 59,
            "price_id": STRIPE_PRICES["US"]
        }

    # 🇪🇺 Europe Logic (Stripe)
    elif country in ["DE", "FR", "EU", "GERMANY", "FRANCE", "ITALY", "SPAIN", "UK"]:
        return {
            "provider": "stripe",
            "currency": "€",
            "price": 39,
            "price_id": STRIPE_PRICES["EU"]
        }

    # 🌎 Default / Global Logic (Stripe)
    else:
        return {
            "provider": "stripe",
            "currency": "$",
            "price": 59,
            "price_id": STRIPE_PRICES["US"]
        }
