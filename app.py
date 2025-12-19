import streamlit as st
from groq import Groq
import base64

# --- 1. CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Gemini Ultra", page_icon="✨", layout="wide")

# --- 2. CSS AGRESIVO (ELIMINA TODO EL TEXTO DEL CLIP) ---
st.markdown("""
    <style>
    header, footer {visibility: hidden;}
    
    /* Centrar contenido */
    .main .block-container { max-width: 850px; padding-bottom: 150px; }

    /* BARRA INFERIOR */
    .stChatFloatingInputContainer {
        bottom: 30px !important;
        background-color: transparent !important;
    }

    /* OCULTAR TEXTOS DEL CARGADOR */
    [data-testid="stFileUploader"] {
        position: absolute;
        left: 10px;
        top: 10px;
        width: 42px;
        z-index: 100;
    }
    
    [data-testid="stFileUploader"] section {
        padding: 0 !important;
        min-height: 40px !important;
        border: none !important;
    }

    /* Desaparecer textos de 'Drag and drop', 'Limit', etc. */
    [data-testid="stFileUploader"] label, 
    [data-testid="stFileUploader"] small, 
    [data-testid="stFileUploader"] div,
    [data-testid="stFileUploaderDropzoneInstructions"] {
        display: none !important;
    }

    /* ESTILIZAR EL BOTÓN COMO UN CLIP CIRCULAR */
    [data-testid="stFileUploader"] button {
        width: 40px !important;
        height: 40px !important;
        border-radius: 50% !important;
        background-color: #f0f2f6 !important;
        color: transparent !important; /* Esconde 'Browse files' */
        border: none !important;
        display: flex !important;
        align-items: center;
        justify-content: center;
    }

    /* Icono de Clip */
    [data-testid="stFileUploader"]::before {
        content: '📎';
        position: absolute;
        left: 10px;
        top: 8px;
        font-size: 20px;
        z-index: 101;
        pointer-events: none;
        color: #444746;
    }

    /* Caja de texto estilo Gemini */
    .stChatInput textarea {
        border-radius: 28px !important;
        padding-left: 55px !important;
        background-color: #f0f2f6 !important;
        border: none !important;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 3. INICIALIZACIÓN SEGURA (EVITA EL KEYERROR) ---
if "chats" not in st.session_state:
    st.session_state.chats = {"Chat 1": []}

if "current_chat" not in st.session_state or st.session_state.current_chat not in st.session_state.chats:
    st.session_state.current_chat = list(st.session_state.chats.keys())[0]

# Conexión Groq
try:
    client = Groq(api_key=st.secrets["GROQ_API_KEY"])
except Exception:
    st.error("Error: Asegúrate de configurar GROQ_API_KEY en los Secrets.")
    st.stop()

# --- 4. SIDEBAR (HISTORIAL) ---
with st.sidebar:
    st.markdown("### ✨ Gemini")
    if st.button("➕ Nuevo chat", use_container_width=True):
        new_name = f"Chat {len(st.session_state.chats) + 1}"
        st.session_state.chats[new_name] = []
        st.session_state.current_chat = new_name
        st.rerun()
    
    st.divider()
    for chat_id in reversed(list(st.session_state.chats.keys())):
        # Botón para cambiar de chat
        if st.button(chat_id, key=f"nav_{chat_id}", use_container_width=True):
            st.session_state.current_chat = chat_id
            st.rerun()

# --- 5. RENDERIZADO DE CHAT ---
st.subheader(st.session_state.current_chat)

# Verificación de seguridad antes de iterar
chat_actual = st.session_state.chats.get(st.session_state.current_chat, [])

for msg in chat_actual:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# --- 6. BARRA DE ENTRADA ---
with st.container():
    # El clip se posiciona automáticamente por CSS
    archivo = st.file_uploader("", type=["pdf", "png", "jpg", "txt", "csv", "xlsx"], label_visibility="collapsed")
    prompt = st.chat_input("Escribe tu mensaje...")

# --- 7. LÓGICA DE RESPUESTA ---
if prompt:
    # Agregar mensaje del usuario
    st.session_state.chats[st.session_state.current_chat].append({"role": "user", "content": prompt})
    
    with st.chat_message("assistant"):
        placeholder = st.empty()
        full_res = ""
        
        # Stream de Groq
        try:
            stream = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": m["content"]} for m in st.session_state.chats[st.session_state.current_chat]],
                stream=True
            )
            
            for chunk in stream:
                if chunk.choices[0].delta.content:
                    full_res += chunk.choices[0].delta.content
                    placeholder.markdown(full_res + "▌")
            
            placeholder.markdown(full_res)
            st.session_state.chats[st.session_state.current_chat].append({"role": "assistant", "content": full_res})
            st.rerun()
        except Exception as e:
            st.error(f"Error en la IA: {e}")
