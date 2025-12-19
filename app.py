import streamlit as st
from memory import store_memory, retrieve_memory
from auth import authenticate_user
from plugins.web import web_search
from plugins.math import solve
from plugins.code import execute_code
from voice import speech_to_text, text_to_speech
from ui.preview import preview
from ui.styles import dark_mode
import os

# Página de configuración
st.set_page_config(page_title="Gemini Chat", page_icon="✨", layout="wide")

# Autenticación (Login)
username = st.text_input("Usuario")
password = st.text_input("Contraseña", type="password")

if authenticate_user(username, password):
    st.success(f"Bienvenido, {username}")
else:
    st.error("Usuario o contraseña incorrectos")

# Tema oscuro
st.markdown(dark_mode(), unsafe_allow_html=True)

# Cargar chat de usuario
chat_history = retrieve_memory(username)

# Mostrar historial de chat
for msg in chat_history:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Input de usuario
message = st.chat_input("Escribe algo...")

if message:
    # Guardar la conversación
    store_memory(message)

    # Llamada a herramientas
    response = ""
    if "buscar en web" in message:
        response = web_search(message)
    elif "resolver" in message:
        response = solve(message)
    elif "ejecutar código" in message:
        response = execute_code(message)
    else:
        response = "Lo siento, no entiendo esa consulta."

    st.chat_message("assistant").markdown(response)

    # Guardar respuesta en la memoria
    store_memory(response)

    # Mostrar vista previa de archivos
    uploaded_files = st.file_uploader("Adjuntar archivos", accept_multiple_files=True)
    if uploaded_files:
        preview(uploaded_files)
