from supabase import create_client
import os

supabase = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_ANON_KEY")
)

def signup(email, password):
    return supabase.auth.sign_up({
        "email": email,
        "password": password
    })

def login(email, password):
    return supabase.auth.sign_in_with_password({
        "email": email,
        "password": password
    })
