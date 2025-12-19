import streamlit as st
from groq import Groq
import base64
import PyPDF2
from datetime import datetime

# --- 1. CONFIGURACIÓN Y CSS AVANZADO ---
st.set_page_config(page_title="Gemini Pro", page_icon="✨", layout="wide")

st.markdown("""
    <style>
    header, footer {visibility: hidden;}
    .main .block-container { max-width: 850px; padding-bottom: 180px; }

    /* Barra inferior fija */
    .stChatFloatingInputContainer {
        bottom: 40px !important;
        background-color: transparent !important;
    }

    /* Estilo del clip (Solo icono) */
    [data-testid="stFileUploader"] {
        position: absolute;
        left: 15px;
        top: 12px;
        width: 40px;
        z-index: 100;
    }
    [data-testid="stFileUploader"] section { padding: 0 !important; min-height: 40px !important; border: none !important; }
    [data-testid="stFileUploader"] label, [data-testid="stFileUploader"] small, 
    [data-testid="stFileUploader"] div, [data-testid="stFileUploaderDropzoneInstructions"] { display: none !important; }
    
    [data-testid="stFileUploader"] button {
        width: 40px !important; height: 40px !important; border-radius: 50% !important;
        background-color: transparent !important; color: transparent !important; border: none !important;
    }
    [data-testid="stFileUploader"]::before {
        content: '📎'; position: absolute; left: 10px; top: 8px; font-size: 20px; z-index: 101; pointer-events: none;
    }

    /* Input de texto */
    .stChatInput textarea {
        border-radius: 28px !important;
        padding-left: 55px !important;
        background-color: #f0f2f6 !important;
        border: none !important;
    }

    /* Miniatura del archivo cargado (Estilo Gemini) */
    .file-preview {
        display: flex;
        align-items: center;
        background-color: #e8f0fe;
        padding: 5px 15px;
        border-radius: 15px;
        margin-bottom: 10px;
        width: fit-content;
        border: 1px solid #1a73e8;
        font-size: 14px;
        color: #1a73e8;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. LÓGICA DE ESTADOS ---
if "chats" not in st.session_state:
    st.session_state.chats = {"Chat 1": []}
if "current_chat" not in st.session_state:
    st.session_state.current_chat = "Chat 1"

client = Groq(api_key=st.secrets["GROQ_API_KEY"])

# --- 3. EXTRACCIÓN DE DATOS ---
def procesar_adjunto(archivo):
    if archivo is None: return None, None
    if "image" in archivo.type:
        return "image", f"data:{archivo.type};base64,{base64.b64encode(archivo.read()).decode()}"
    elif "pdf" in archivo.type:
        reader = PyPDF2.PdfReader(archivo)
        return "text", "CONTENIDO PDF: " + "\n".join([p.extract_text() for p in reader.pages])
    else:
        return "text", archivo.read().decode()

# --- 4. SIDEBAR ---
with st.sidebar:
    st.title("✨ Gemini")
    if st.button("➕ Nuevo chat", use_container_width=True):
        name = f"Chat {len(st.session_state.chats) + 1}"
        st.session_state.chats[name] = []
        st.session_state.current_chat = name
        st.rerun()
    st.divider()
    for c in reversed(list(st.session_state.chats.keys())):
        if st.button(c, key=f"nav_{c}", use_container_width=True):
            st.session_state.current_chat = c
            st.rerun()

# --- 5. RENDER CHAT ---
st.subheader(st.session_state.current_chat)
chat_actual = st.session_state.chats[st.session_state.current_chat]

for m in chat_actual:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

# --- 6. BARRA INFERIOR CON PREVISUALIZACIÓN ---
with st.container():
    # Área de previsualización de archivo
    archivo = st.file_uploader("", type=["pdf", "png", "jpg", "txt"], label_visibility="collapsed")
    
    if archivo is not None:
        st.markdown(f'<div class="file-preview">📄 {archivo.name} listo para analizar</div>', unsafe_allow_html=True)
    
    prompt = st.chat_input("Escribe tu consulta aquí...")

# --- 7. EJECUCIÓN ---
if prompt:
    chat_actual.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Procesar archivo
    tipo, contenido = procesar_adjunto(archivo)

    with st.chat_message("assistant"):
        placeholder = st.empty()
        full_res = ""
        
        # Configurar mensajes para la IA
        if tipo == "image":
            modelo = "llama-3.2-11b-vision-preview"
            mensajes = [
                {"role": "user", "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": contenido}}
                ]}
            ]
        else:
            modelo = "llama-3.3-70b-versatile"
            contexto = f"CONTEXTO DEL ARCHIVO: {contenido}\n\n" if contenido else ""
            mensajes = [{"role": "user", "content": f"{contexto}{prompt}"}]

        # Llamada a Groq
        try:
            stream = client.chat.completions.create(model=modelo, messages=mensajes, stream=True)
            for chunk in stream:
                if chunk.choices[0].delta.content:
                    full_res += chunk.choices[0].delta.content
                    placeholder.markdown(full_res + "▌")
            placeholder.markdown(full_res)
            chat_actual.append({"role": "assistant", "content": full_res})
        except Exception as e:
            st.error(f"Error: {e}")
