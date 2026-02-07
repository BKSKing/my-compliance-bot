def get_payment_provider(country):
    country = country.lower()

    if country == "india":
        return "razorpay"

    return "stripe"
