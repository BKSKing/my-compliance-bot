from supabase import create_client
import os

# ---------------- SUPABASE CLIENT ----------------
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

# ---------------- USER FUNCTIONS ----------------

def get_user(email):
    res = supabase.table("users").select("*").eq("email", email).single().execute()
    return res.data

def create_user(user_id, email, country=""):
    supabase.table("users").insert({
        "id": user_id,
        "email": email,
        "country": country,
        "plan": "free",
        "subscription_status": "inactive",
        "scans_used": 0
    }).execute()

def increment_scan(email):
    user = get_user(email)
    supabase.table("users").update({
        "scans_used": user["scans_used"] + 1
    }).eq("email", email).execute()

def update_user_to_pro(email, provider):
    supabase.table("users").update({
        "plan": "pro",
        "subscription_status": "active",
        "payment_provider": provider
    }).eq("email", email).execute()

