from supabase import create_client
import os

supabase = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_ANON_KEY")
)

def get_user(email):
    res = supabase.table("users").select("*").eq("email", email).execute()
    if res.data:
        return res.data[0]
    return None

def create_user(user_id, email):
    supabase.table("users").insert({
        "id": user_id,
        "email": email,
        "plan": "free",
        "scans_used": 0
    }).execute()

def increment_scan(email):
    user = get_user(email)
    if user:
        supabase.table("users") \
            .update({"scans_used": user["scans_used"] + 1}) \
            .eq("email", email) \
            .execute()
