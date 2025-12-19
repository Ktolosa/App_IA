import streamlit as st
from groq import Groq
import base64
from datetime import datetime

# --- 1. CONFIGURACIÓN Y ESTILO GEMINI ---
st.set_page_config(page_title="Gemini", page_icon="✨", layout="wide")

st.markdown("""
    <style>
    /* Ocultar textos del cargador de archivos */
    [data-testid="stFileUploader"] section { padding: 0 !important; min-height: 0 !important; border: none !important; }
    [data-testid="stFileUploader"] label, [data-testid="stFileUploader"] small, 
    [data-testid="stFileUploader"] div[data-testid="stMarkdownContainer"] { display: none !important; }
    
    /* Estilizar el botón para que sea solo el clip */
    [data-testid="stFileUploader"] button {
        border: none !important;
        background-color: #f0f2f6 !important;
        border-radius: 50% !important;
        color: transparent !important;
        width: 40px !important;
        height: 40px !important;
    }
    [data-testid="stFileUploader"] button::after {
        content: '📎';
        color: #444746;
        font-size: 20px;
        position: absolute;
        top: 50%; left: 50%;
        transform: translate(-50%, -50%);
    }

    /* Fijar la barra de entrada al fondo de forma limpia */
    .footer-container {
        position: fixed;
        bottom: 0;
        left: 0;
        right: 0;
        background: white;
        padding: 20px 100px;
        z-index: 1000;
    }
    
    /* Ajustar el área de mensajes para que no se tape */
    .main-chat-container {
        margin-bottom: 120px;
        max-width: 850px;
        margin-left: auto;
        margin-right: auto;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. LÓGICA DE SESIÓN (HISTORIAL) ---
if "chats" not in st.session_state:
    st.session_state.chats = {"Nuevo Chat": []}
if "active_chat" not in st.session_state:
    st.session_state.active_chat = "Nuevo Chat"

client = Groq(api_key=st.secrets["GROQ_API_KEY"])

# --- 3. BARRA LATERAL (GEMINI STYLE) ---
with st.sidebar:
    st.title("✨ Gemini")
    if st.button("➕ Nuevo chat", use_container_width=True):
        nuevo_nombre = f"Chat {len(st.session_state.chats) + 1}"
        st.session_state.chats[nuevo_nombre] = []
        st.session_state.active_chat = nuevo_nombre
        st.rerun()
    
    st.divider()
    for chat_name in reversed(list(st.session_state.chats.keys())):
        if st.button(chat_name, key=chat_name, use_container_width=True):
            st.session_state.active_chat = chat_name
            st.rerun()

# --- 4. ÁREA DE CHAT ---
st.markdown('<div class="main-chat-container">', unsafe_allow_html=True)
for msg in st.session_state.chats[st.session_state.active_chat]:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
st.markdown('</div>', unsafe_allow_html=True)

# --- 5. BARRA INFERIOR FIJA ---
# Usamos un contenedor vacío para empujar el contenido
st.write("<br><br><br>", unsafe_allow_html=True)

with st.container():
    # Creamos columnas para el clip y el texto
    col_clip, col_input = st.columns([0.05, 0.95])
    
    with col_clip:
        # El CSS arriba lo convierte en solo el clip
        archivo = st.file_uploader("", type=["pdf", "png", "jpg", "txt", "csv", "xlsx"], label_visibility="collapsed")
    
    with col_input:
        prompt = st.chat_input("Escribe tu mensaje aquí...")

# --- 6. PROCESAMIENTO DE RESPUESTA ---
if prompt:
    # Guardar mensaje del usuario
    st.session_state.chats[st.session_state.active_chat].append({"role": "user", "content": prompt})
    
    # Generar respuesta
    with st.chat_message("assistant"):
        placeholder = st.empty()
        full_response = ""
        
        # Llamada a Groq (Modelo más potente 70B)
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            stream=True
        )
        
        for chunk in completion:
            if chunk.choices[0].delta.content:
                full_response += chunk.choices[0].delta.content
                placeholder.markdown(full_response + "▌")
        
        placeholder.markdown(full_response)
        st.session_state.chats[st.session_state.active_chat].append({"role": "assistant", "content": full_response})
        st.rerun()
