import streamlit as st
from groq import Groq
import base64

# --- 1. CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Gemini", page_icon="✨", layout="wide")

# --- 2. CSS AVANZADO (OCULTA TODO EL TEXTO Y ESTILIZA LA BARRA) ---
st.markdown("""
    <style>
    /* Ocultar header y footer de Streamlit */
    header, footer {visibility: hidden;}
    
    /* Contenedor principal de mensajes */
    .main .block-container {
        max-width: 850px;
        padding-bottom: 150px;
    }

    /* ESTILO DE LA BARRA INFERIOR (ISLA GEMINI) */
    .stChatFloatingInputContainer {
        bottom: 30px !important;
        background-color: transparent !important;
    }
    
    /* CAJA DE TEXTO REDONDEADA */
    .stChatInput textarea {
        border-radius: 28px !important;
        padding: 15px 15px 15px 50px !important;
        background-color: #f0f2f6 !important;
        border: none !important;
        line-height: 1.5 !important;
    }

    /* ELIMINAR TEXTOS DEL CARGADOR DE ARCHIVOS POR COMPLETO */
    [data-testid="stFileUploader"] {
        position: absolute;
        left: 10px;
        top: 10px;
        width: 40px;
        z-index: 100;
    }
    
    /* Hacemos el cargador invisible pero clickeable */
    [data-testid="stFileUploader"] section {
        padding: 0 !important;
        min-height: 40px !important;
        border: none !important;
        background: transparent !important;
    }
    
    [data-testid="stFileUploader"] label, 
    [data-testid="stFileUploader"] small, 
    [data-testid="stFileUploader"] div,
    [data-testid="stFileUploaderDropzoneInstructions"] {
        display: none !important;
    }

    /* CREAR EL ICONO DE CLIP SOBRE EL BOTÓN INVISIBLE */
    [data-testid="stFileUploader"] button {
        width: 40px !important;
        height: 40px !important;
        border-radius: 50% !important;
        background-color: transparent !important;
        color: transparent !important;
        border: none !important;
    }

    [data-testid="stFileUploader"]::before {
        content: '📎';
        position: absolute;
        left: 10px;
        top: 8px;
        font-size: 20px;
        pointer-events: none; /* Permite que el click pase al botón de abajo */
        color: #444746;
    }

    /* Sidebar Estilo Gemini */
    [data-testid="stSidebar"] {
        background-color: #f8f9fa;
        border-right: 1px solid #e0e0e0;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 3. LÓGICA DE CHATS ---
if "chats" not in st.session_state:
    st.session_state.chats = {"Nuevo Chat": []}
if "current_chat" not in st.session_state:
    st.session_state.current_chat = "Nuevo Chat"

client = Groq(api_key=st.secrets["GROQ_API_KEY"])

# --- 4. SIDEBAR (HISTORIAL) ---
with st.sidebar:
    st.markdown("<h2 style='padding: 0;'>✨ Gemini</h2>", unsafe_allow_html=True)
    if st.button("➕ Nuevo chat", use_container_width=True):
        name = f"Chat {len(st.session_state.chats) + 1}"
        st.session_state.chats[name] = []
        st.session_state.current_chat = name
        st.rerun()
    
    st.divider()
    for chat_id in reversed(list(st.session_state.chats.keys())):
        if st.button(chat_id, key=chat_id, use_container_width=True):
            st.session_state.current_chat = chat_id
            st.rerun()

# --- 5. PANTALLA DE CHAT ---
st.subheader(st.session_state.current_chat)

# Mostrar mensajes
for msg in st.session_state.chats[st.session_state.current_chat]:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# --- 6. BARRA INFERIOR INTEGRADA ---
# El clip se posiciona automáticamente por el CSS arriba
with st.container():
    archivo = st.file_uploader("", type=["pdf", "png", "jpg", "csv", "xlsx", "txt"], label_visibility="collapsed")
    prompt = st.chat_input("Escribe tu mensaje aquí...")

# --- 7. RESPUESTA DE IA ---
if prompt:
    st.session_state.chats[st.session_state.current_chat].append({"role": "user", "content": prompt})
    
    with st.chat_message("assistant"):
        placeholder = st.empty()
        full_res = ""
        
        # Usamos Groq con streaming
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            stream=True
        )
        
        for chunk in completion:
            if chunk.choices[0].delta.content:
                full_res += chunk.choices[0].delta.content
                placeholder.markdown(full_res + "▌")
        
        placeholder.markdown(full_res)
        st.session_state.chats[st.session_state.current_chat].append({"role": "assistant", "content": full_res})
        st.rerun()
