import streamlit_authenticator as stauth
from supabase import create_client
import os

def authenticate_user(username, password):
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_API_KEY")
    client = create_client(url, key)
    
    # Verificar si el usuario está registrado en la base de datos
    user = client.table('users').select('*').eq('username', username).execute()
    if user:
        stored_password = user[0]['password']
        return stauth.Hasher([password]).check(stored_password)
    return False
