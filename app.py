import streamlit as st
from groq import Groq
import base64
from datetime import datetime

# --- 1. CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Gemini", page_icon="✨", layout="wide")

# --- 2. CSS AVANZADO (REDiseño de Interfaz) ---
st.markdown("""
    <style>
    /* Ocultar elementos molestos de Streamlit */
    #MainMenu, footer, header {visibility: hidden;}
    .stApp { background-color: #ffffff; }

    /* Contenedor del Chat (Centro) */
    .main-chat {
        max-width: 800px;
        margin: 0 auto;
        padding-bottom: 150px;
    }

    /* BURBUJAS DE MENSAJE ESTILO GEMINI */
    .stChatMessage {
        background-color: transparent !important;
        border: none !important;
        margin-top: 20px !important;
    }
    
    /* BARRA INFERIOR (ISLA FLOTANTE) */
    .stChatFloatingInputContainer {
        bottom: 40px !important;
        background-color: transparent !important;
        border: none !important;
    }
    
    div[data-testid="stForm"] {
        border: 1px solid #e0e0e0 !important;
        border-radius: 28px !important;
        padding: 8px 20px !important;
        background-color: #f0f2f6 !important;
        box-shadow: 0 1px 6px rgba(32,33,36,.28);
    }

    /* EL CLIP (SOLO ICONO) */
    [data-testid="stFileUploader"] {
        width: 40px;
        position: absolute;
        left: 10px;
        top: 5px;
        z-index: 10;
    }
    [data-testid="stFileUploader"] section { padding: 0 !important; min-height: 0 !important; border: none !important; }
    [data-testid="stFileUploader"] label, [data-testid="stFileUploader"] small, 
    [data-testid="stFileUploader"] div[data-testid="stMarkdownContainer"] { display: none !important; }
    
    [data-testid="stFileUploader"] button {
        background: transparent !important;
        color: transparent !important;
        border: none !important;
        font-size: 0 !important;
    }
    [data-testid="stFileUploader"] button::after {
        content: '📎';
        color: #444746;
        font-size: 22px;
        visibility: visible;
    }

    /* AJUSTE DEL TEXTO DE ENTRADA */
    .stChatInput textarea {
        padding-left: 45px !important;
        background-color: transparent !important;
        border: none !important;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 3. LÓGICA DE DATOS ---
if "chats" not in st.session_state:
    st.session_state.chats = {"Chat Inicial": []}
if "active_chat" not in st.session_state:
    st.session_state.active_chat = "Chat Inicial"

# Inicializar Groq (Asegúrate de tener la KEY en secrets)
try:
    client = Groq(api_key=st.secrets["GROQ_API_KEY"])
except:
    st.error("Error: Configura GROQ_API_KEY en los Secrets de Streamlit.")
    st.stop()

# --- 4. SIDEBAR (HISTORIAL) ---
with st.sidebar:
    st.markdown("<h2 style='text-align: center;'>✨ Gemini</h2>", unsafe_allow_html=True)
    if st.button("➕ Nuevo chat", use_container_width=True):
        nuevo_id = f"Chat {datetime.now().strftime('%H:%M:%S')}"
        st.session_state.chats[nuevo_id] = []
        st.session_state.active_chat = nuevo_id
        st.rerun()
    
    st.divider()
    st.write("Recientes")
    for chat_id in reversed(list(st.session_state.chats.keys())):
        if st.button(chat_id, key=chat_id, use_container_width=True):
            st.session_state.active_chat = chat_id
            st.rerun()

# --- 5. VISUALIZACIÓN DE MENSAJES ---
st.markdown('<div class="main-chat">', unsafe_allow_html=True)
for msg in st.session_state.chats[st.session_state.active_chat]:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
st.markdown('</div>', unsafe_allow_html=True)

# --- 6. BARRA DE ENTRADA (CLIP + INPUT) ---
# Colocamos el uploader y el input "encimados" visualmente con CSS
with st.container():
    col_input = st.columns([1])[0]
    with col_input:
        # El clip se posiciona mediante el CSS de arriba
        archivo = st.file_uploader("", type=["pdf", "png", "jpg", "txt", "csv", "xlsx"], label_visibility="collapsed")
        prompt = st.chat_input("Escribe tu mensaje aquí...")

# --- 7. PROCESAMIENTO ---
if prompt:
    # Agregar mensaje de usuario
    st.session_state.chats[st.session_state.active_chat].append({"role": "user", "content": prompt})
    
    with st.chat_message("assistant"):
        res_placeholder = st.empty()
        full_res = ""
        
        # Stream de Groq
        stream = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            stream=True,
        )
        
        for chunk in stream:
            if chunk.choices[0].delta.content:
                full_res += chunk.choices[0].delta.content
                res_placeholder.markdown(full_res + "▌")
        
        res_placeholder.markdown(full_res)
        st.session_state.chats[st.session_state.active_chat].append({"role": "assistant", "content": full_res})
        st.rerun()
