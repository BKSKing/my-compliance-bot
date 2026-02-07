def get_pricing(country):
    country = country.lower()

    if country == "india":
        return {"currency": "₹", "price": 1299}

    if country in ["nigeria", "kenya", "ghana", "south africa"]:
        return {"currency": "$", "price": 9}

    if country in ["indonesia", "vietnam", "philippines", "thailand"]:
        return {"currency": "$", "price": 12}

    if country in ["germany", "france", "italy", "spain", "uk"]:
        return {"currency": "€", "price": 39}

    if country in ["united states", "usa", "canada"]:
        return {"currency": "$", "price": 59}

    return {"currency": "$", "price": 59}  # default
