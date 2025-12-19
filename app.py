import streamlit as st
from groq import Groq
import base64
import PyPDF2
from datetime import datetime

# --- 1. CONFIGURACIÓN Y CSS (ALINEACIÓN GEMINI DEFINITIVA) ---
st.set_page_config(page_title="Gemini Ultra", page_icon="✨", layout="wide")

st.markdown("""
    <style>
    header, footer {visibility: hidden;}
    .main .block-container { max-width: 850px; padding-bottom: 180px; }

    /* CONTENEDOR FLOTANTE INFERIOR */
    .stChatFloatingInputContainer {
        bottom: 30px !important;
        background-color: white !important;
        padding: 15px 0 !important;
    }

    /* ALINEACIÓN EN FILA: CLIP + INPUT */
    [data-testid="stForm"] {
        display: flex !important;
        align-items: flex-end !important;
        gap: 10px !important;
        border: none !important;
        padding: 0 !important;
    }

    /* LIMPIEZA TOTAL DEL CARGADOR DE ARCHIVOS */
    [data-testid="stFileUploader"] {
        width: 45px !important;
        margin-bottom: 5px !important;
    }
    
    [data-testid="stFileUploader"] section { padding: 0 !important; min-height: 0 !important; border: none !important; background: transparent !important; }
    [data-testid="stFileUploader"] label, [data-testid="stFileUploader"] small, 
    [data-testid="stFileUploader"] div, [data-testid="stFileUploaderDropzoneInstructions"] { 
        display: none !important; 
    }

    /* BOTÓN CIRCULAR CON CLIP */
    [data-testid="stFileUploader"] button {
        background-color: #f0f2f6 !important;
        color: transparent !important;
        border: none !important;
        width: 42px !important;
        height: 42px !important;
        border-radius: 50% !important;
    }
    
    [data-testid="stFileUploader"] button::after {
        content: '📎';
        color: #444746;
        font-size: 20px;
        position: absolute;
        top: 50%; left: 50%;
        transform: translate(-50%, -50%);
        visibility: visible;
    }

    /* BARRA DE TEXTO GEMINI */
    .stChatInput { flex-grow: 1 !important; }
    .stChatInput textarea {
        border-radius: 24px !important;
        background-color: #f0f2f6 !important;
        border: none !important;
        padding-top: 12px !important;
    }

    /* PÍLDORAS DE ARCHIVOS (Encima de la barra) */
    .pill-container {
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
        margin-bottom: 10px;
        max-width: 800px;
    }
    .file-pill {
        background-color: #e8f0fe;
        color: #1a73e8;
        padding: 5px 12px;
        border-radius: 15px;
        font-size: 0.85rem;
        border: 1px solid #c2e7ff;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. GESTIÓN DE ESTADOS ---
if "chats" not in st.session_state:
    st.session_state.chats = {"Chat 1": []}
if "current_chat" not in st.session_state:
    st.session_state.current_chat = "Chat 1"

client = Groq(api_key=st.secrets["GROQ_API_KEY"])

# --- 3. PROCESADOR MULTI-ARCHIVO ---
def procesar_archivos_batch(archivos_lista):
    contexto = ""
    imgs = []
    for f in archivos_lista:
        if "image" in f.type:
            b64 = base64.b64encode(f.read()).decode()
            imgs.append(f"data:{f.type};base64,{b64}")
        elif "pdf" in f.type:
            reader = PyPDF2.PdfReader(f)
            contexto += f"\n[Doc: {f.name}]\n" + " ".join([p.extract_text() for p in reader.pages])
        else:
            contexto += f"\n[Doc: {f.name}]\n" + f.read().decode()
    return contexto, imgs

# --- 4. SIDEBAR ---
with st.sidebar:
    st.markdown("### ✨ Gemini")
    if st.button("➕ Nuevo chat", use_container_width=True):
        name = f"Chat {len(st.session_state.chats) + 1}"
        st.session_state.chats[name] = []
        st.session_state.current_chat = name
        st.rerun()
    st.divider()
    for c_id in reversed(list(st.session_state.chats.keys())):
        if st.button(c_id, key=f"nav_{c_id}", use_container_width=True):
            st.session_state.current_chat = c_id
            st.rerun()

# --- 5. RENDERIZADO DE CHAT ---
st.subheader(st.session_state.current_chat)
history = st.session_state.chats[st.session_state.current_chat]

for m in history:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

# --- 6. BARRA INFERIOR (CLIP + MULTIPÍLDORAS + INPUT) ---
with st.container():
    # Visualización de archivos cargados
    archivos = st.file_uploader("", type=["pdf", "png", "jpg", "txt", "csv"], 
                                 accept_multiple_files=True, label_visibility="collapsed")
    
    if archivos:
        st.markdown('<div class="pill-container">', unsafe_allow_html=True)
        for f in archivos:
            st.markdown(f'<div class="file-pill">📄 {f.name}</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    
    prompt = st.chat_input("Escribe tu consulta aquí...")

# --- 7. LÓGICA DE RESPUESTA ACTUALIZADA ---
if prompt:
    history.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    contexto_texto, lista_imgs = procesar_archivos_batch(archivos)

    with st.chat_message("assistant"):
        placeholder = st.empty()
        full_res = ""
        
        # MODELO ACTUALIZADO (LLAMA 3.2 90B VISION)
        if lista_imgs:
            modelo = "llama-3.2-90b-vision-preview" 
            # Combinamos texto y todas las imágenes
            cont_api = [{"type": "text", "text": f"{contexto_texto}\n\n{prompt}"}]
            for img_url in lista_imgs:
                cont_api.append({"type": "image_url", "image_url": {"url": img_url}})
            mensajes_api = [{"role": "user", "content": cont_api}]
        else:
            modelo = "llama-3.3-70b-versatile"
            mensajes_api = [{"role": "user", "content": f"{contexto_texto}\n\n{prompt}"}]

        try:
            stream = client.chat.completions.create(model=modelo, messages=mensajes_api, stream=True)
            for chunk in stream:
                if chunk.choices[0].delta.content:
                    full_res += chunk.choices[0].delta.content
                    placeholder.markdown(full_res + "▌")
            placeholder.markdown(full_res)
            history.append({"role": "assistant", "content": full_res})
            st.rerun()
        except Exception as e:
            st.error(f"Error de conexión: {e}")
