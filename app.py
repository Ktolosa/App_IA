import streamlit as st
from groq import Groq
import base64
import pandas as pd
import plotly.express as px
from datetime import datetime

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Gemini Pro", page_icon="✨", layout="wide")

# --- CSS RADICAL PARA INTERFAZ LIMPIA ---
st.markdown("""
    <style>
    /* 1. Ocultar absolutamente todo el texto del cargador */
    [data-testid="stFileUploader"] section { padding: 0 !important; min-height: 0 !important; border: none !important; }
    [data-testid="stFileUploader"] label, [data-testid="stFileUploader"] small, 
    [data-testid="stFileUploader"] div, [data-testid="stMarkdownContainer"] { 
        display: none !important; 
    }
    
    /* 2. Convertir el botón en un círculo pequeño con clip */
    [data-testid="stFileUploader"] button {
        border: 1px solid #dcdcdc !important;
        background-color: white !important;
        border-radius: 50% !important;
        color: transparent !important;
        width: 38px !important;
        height: 38px !important;
        overflow: hidden !important;
    }
    [data-testid="stFileUploader"] button::after {
        content: '📎';
        color: #5f6368;
        font-size: 18px;
        position: absolute;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
    }

    /* 3. Fijar la barra de chat AL FONDO */
    div[data-testid="stForm"] {
        border: none !important;
        padding: 0 !important;
    }
    
    .stChatFloatingInputContainer {
        position: fixed !important;
        bottom: 20px !important;
        padding: 10px 0 !important;
        background: white !important;
    }

    /* 4. Estilo de los globos de texto */
    .stChatMessage {
        background-color: #f0f2f6 !important;
        border-radius: 15px !important;
        margin-bottom: 10px !important;
    }
    </style>
    """, unsafe_allow_html=True)

# --- INICIALIZACIÓN ---
client = Groq(api_key=st.secrets["GROQ_API_KEY"])

if "all_chats" not in st.session_state:
    st.session_state.all_chats = {"Chat 1": []}
if "current_chat" not in st.session_state:
    st.session_state.current_chat = "Chat 1"

# --- SIDEBAR (HISTORIAL) ---
with st.sidebar:
    st.title("✨ Gemini")
    if st.button("➕ Nuevo Chat", use_container_width=True):
        new_id = f"Chat {len(st.session_state.all_chats) + 1}"
        st.session_state.all_chats[new_id] = []
        st.session_state.current_chat = new_id
        st.rerun()
    st.divider()
    for chat_id in reversed(list(st.session_state.all_chats.keys())):
        if st.button(chat_id, key=f"nav_{chat_id}"):
            st.session_state.current_chat = chat_id
            st.rerun()

# --- ÁREA DE MENSAJES ---
# Contenedor para que el scroll funcione bien y no tape la barra
chat_placeholder = st.container()
with chat_placeholder:
    for msg in st.session_state.all_chats[st.session_state.current_chat]:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if "chart" in msg: st.plotly_chart(msg["chart"])

# Espacio amortiguador para que el chat no se meta debajo de la barra fija
st.write("<div style='height: 120px;'></div>", unsafe_allow_html=True)

# --- BARRA DE ENTRADA (POSICIONADA ABAJO) ---
# Usamos una columna para alinear el clip y el texto perfectamente
footer = st.container()
with footer:
    col_icon, col_input = st.columns([0.05, 0.95])
    with col_icon:
        # El CSS arriba hace que esto sea SOLO el clip
        archivo = st.file_uploader("", type=["pdf", "png", "jpg", "csv", "xlsx", "txt"], label_visibility="collapsed")
    with col_input:
        prompt = st.chat_input("Escribe tu mensaje...")

# --- PROCESAMIENTO ---
if prompt:
    st.session_state.all_chats[st.session_state.current_chat].append({"role": "user", "content": prompt})
    
    with st.chat_message("assistant"):
        # Detectar si hay archivo para usar modelo Vision o Texto
        modelo = "llama-3.3-70b-versatile" 
        full_res = ""
        res_box = st.empty()
        
        # Llamada a la API
        completion = client.chat.completions.create(
            model=modelo,
            messages=[{"role": "user", "content": prompt}],
            stream=True
        )
        
        for chunk in completion:
            if chunk.choices[0].delta.content:
                full_res += chunk.choices[0].delta.content
                res_box.markdown(full_res + "▌")
        res_box.markdown(full_res)
        
        # Lógica de Gráficos (Si el usuario los pide)
        new_msg = {"role": "assistant", "content": full_res}
        if "gráfico" in prompt.lower() or "pastel" in prompt.lower():
            # Datos de ejemplo basados en tu prompt anterior
            data = {"Almacenaje": 30, "Manejo": 20, "Multas": 15, "Aduana": 15, "Otros": 20}
            fig = px.pie(names=list(data.keys()), values=list(data.values()), hole=0.4, title="Distribución de Tarifas")
            st.plotly_chart(fig)
            new_msg["chart"] = fig

        st.session_state.all_chats[st.session_state.current_chat].append(new_msg)
        st.rerun()
