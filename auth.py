from supabase import create_client
import os

supabase = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_ANON_KEY")
)

def signup(email, password):
    if not email or not password:
        return {"error": "Email and password required"}

    if len(password) < 6:
        return {"error": "Password must be at least 6 characters"}

    return supabase.auth.sign_up({
        "email": email.strip(),
        "password": password
    })

def login(email, password):
    if not email or not password:
        return {"error": "Email and password required"}

    try:
        res = supabase.auth.sign_in_with_password({
            "email": email.strip(),
            "password": password
        })
        return res
    except Exception as e:
        return {"error": str(e)}


