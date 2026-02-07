def get_pricing(country):
    country = country.lower()

    if country == "india":
        return {
            "currency": "₹",
            "price": 1299,
            "provider": "razorpay"
        }

    if country in ["germany", "france", "italy", "spain", "uk"]:
        return {
            "currency": "€",
            "price": 39,
            "provider": "stripe"
        }

    return {
        "currency": "$",
        "price": 59,
        "provider": "stripe"
    }
