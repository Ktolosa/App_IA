import streamlit as st
from groq import Groq
import base64
import PyPDF2
from datetime import datetime

# --- 1. CONFIGURACIÓN Y CSS RADICAL ---
st.set_page_config(page_title="Gemini", page_icon="✨", layout="wide")

st.markdown("""
    <style>
    /* Ocultar ruidos de Streamlit */
    header, footer {visibility: hidden;}
    .main .block-container { max-width: 900px; padding-bottom: 120px; }

    /* 1. POSICIONAR LA BARRA AL FONDO Y ALINEAR HIJOS */
    .stChatFloatingInputContainer {
        bottom: 30px !important;
        background-color: transparent !important;
        display: flex !important;
        align-items: flex-end !important;
        justify-content: center !important;
        gap: 10px !important;
    }

    /* 2. LIMPIAR EL CARGADOR DE ARCHIVOS (SOLO ICONO) */
    [data-testid="stFileUploader"] {
        width: 46px !important;
        margin-bottom: 4px !important; /* Alineación fina con la barra */
    }
    
    [data-testid="stFileUploader"] section { 
        padding: 0 !important; 
        min-height: 0 !important; 
        border: none !important; 
        background: transparent !important; 
    }
    
    /* Eliminar textos molestos */
    [data-testid="stFileUploader"] label, 
    [data-testid="stFileUploader"] small, 
    [data-testid="stFileUploader"] div[data-testid="stMarkdownContainer"],
    [data-testid="stFileUploaderDropzoneInstructions"] { 
        display: none !important; 
    }

    /* Convertir el botón de 'Browse' en un círculo con clip */
    [data-testid="stFileUploader"] button {
        border: none !important;
        background-color: #f0f2f6 !important;
        border-radius: 50% !important;
        color: transparent !important;
        width: 44px !important;
        height: 44px !important;
        transition: 0.3s;
    }
    
    [data-testid="stFileUploader"] button:hover { background-color: #e2e4e9 !important; }

    [data-testid="stFileUploader"] button::after {
        content: '📎';
        color: #444746;
        font-size: 20px;
        position: absolute;
        top: 50%; left: 50%;
        transform: translate(-50%, -50%);
        visibility: visible;
    }

    /* 3. ESTILO DE LA BARRA DE TEXTO */
    .stChatInput {
        flex-grow: 1 !important;
        width: 100% !important;
    }

    .stChatInput textarea {
        border-radius: 28px !important;
        background-color: #f0f2f6 !important;
        border: none !important;
        padding-top: 12px !important;
    }

    /* Píldora de archivo cargado */
    .file-pill {
        background-color: #e8f0fe;
        color: #1a73e8;
        padding: 6px 16px;
        border-radius: 20px;
        font-size: 0.9rem;
        border: 1px solid #c2e7ff;
        margin-bottom: 10px;
        display: inline-flex;
        align-items: center;
        gap: 8px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. LÓGICA DE ESTADOS ---
if "chats" not in st.session_state:
    st.session_state.chats = {"Chat 1": []}
if "active_chat" not in st.session_state:
    st.session_state.active_chat = "Chat 1"

client = Groq(api_key=st.secrets["GROQ_API_KEY"])

# --- 3. PROCESAMIENTO MULTIMODAL ---
def procesar_todo(file):
    if not file: return None, None
    if "image" in file.type:
        return "image", f"data:{file.type};base64,{base64.b64encode(file.read()).decode()}"
    if "pdf" in file.type:
        reader = PyPDF2.PdfReader(file)
        return "text", "INFO PDF: " + " ".join([p.extract_text() for p in reader.pages])
    return "text", file.read().decode()

# --- 4. SIDEBAR ---
with st.sidebar:
    st.markdown("### ✨ Gemini")
    if st.button("➕ Nuevo chat", use_container_width=True):
        nuevo = f"Chat {len(st.session_state.chats) + 1}"
        st.session_state.chats[nuevo] = []
        st.session_state.active_chat = nuevo
        st.rerun()
    st.divider()
    for c_id in reversed(list(st.session_state.chats.keys())):
        if st.button(c_id, key=f"nav_{c_id}", use_container_width=True):
            st.session_state.active_chat = c_id
            st.rerun()

# --- 5. CHAT VIEW ---
st.subheader(st.session_state.active_chat)
history = st.session_state.chats[st.session_state.active_chat]

for m in history:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

# --- 6. BARRA INFERIOR INTEGRADA ---
with st.container():
    # El archivo subido se detecta aquí
    archivo = st.file_uploader("", type=["pdf", "png", "jpg", "txt"], label_visibility="collapsed")
    
    if archivo:
        st.markdown(f'<div class="file-pill">📄 {archivo.name}</div>', unsafe_allow_html=True)
    
    # La magia: El chat_input se posiciona junto al uploader por el CSS de flex-end
    prompt = st.chat_input("Escribe tu mensaje...")

# --- 7. RESPUESTA ---
if prompt:
    history.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    tipo, contenido = procesar_todo(archivo)

    with st.chat_message("assistant"):
        modelo = "llama-3.2-11b-vision-preview" if tipo == "image" else "llama-3.3-70b-versatile"
        
        if tipo == "image":
            msgs = [{"role": "user", "content": [{"type": "text", "text": prompt}, {"type": "image_url", "image_url": {"url": contenido}}]}]
        else:
            ctx = f"CONTEXTO DEL ARCHIVO: {contenido}\n\n" if contenido else ""
            msgs = [{"role": "user", "content": f"{ctx}{prompt}"}]

        full_res = ""
        placeholder = st.empty()
        stream = client.chat.completions.create(model=modelo, messages=msgs, stream=True)
        
        for chunk in stream:
            if chunk.choices[0].delta.content:
                full_res += chunk.choices[0].delta.content
                placeholder.markdown(full_res + "▌")
        
        placeholder.markdown(full_res)
        history.append({"role": "assistant", "content": full_res})
        st.rerun()
