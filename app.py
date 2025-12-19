import streamlit as st
from groq import Groq
import base64
import PyPDF2
from datetime import datetime

# --- 1. CONFIGURACIÓN Y CSS (ALINEACIÓN IZQUIERDA Y MULTIPÍLDORAS) ---
st.set_page_config(page_title="Gemini Ultra Multi", page_icon="✨", layout="wide")

st.markdown("""
    <style>
    header, footer {visibility: hidden;}
    .main .block-container { max-width: 850px; padding-bottom: 200px; }

    /* CONTENEDOR DE ENTRADA FIJO */
    .stChatFloatingInputContainer {
        bottom: 30px !important;
        background-color: transparent !important;
    }

    /* POSICIONAR EL CARGADOR DENTRO DE LA BARRA A LA IZQUIERDA */
    [data-testid="stFileUploader"] {
        position: absolute;
        left: 20px;
        top: 10px;
        width: 40px;
        z-index: 1000;
    }
    
    [data-testid="stFileUploader"] section { padding: 0 !important; min-height: 0 !important; border: none !important; background: transparent !important; }
    [data-testid="stFileUploader"] label, [data-testid="stFileUploader"] small, 
    [data-testid="stFileUploader"] div, [data-testid="stFileUploaderDropzoneInstructions"] { 
        display: none !important; 
    }

    [data-testid="stFileUploader"] button {
        background-color: transparent !important;
        color: transparent !important;
        border: none !important;
        width: 40px !important;
        height: 40px !important;
    }
    
    [data-testid="stFileUploader"] button::before {
        content: '📎';
        color: #444746;
        font-size: 20px;
        position: absolute;
        left: 10px;
        top: 8px;
        visibility: visible;
    }

    /* ESTILO DE LA BARRA DE TEXTO */
    .stChatInput textarea {
        border-radius: 28px !important;
        background-color: #f0f2f6 !important;
        border: none !important;
        padding-left: 55px !important;
        padding-top: 12px !important;
    }

    /* CONTENEDOR DE PÍLDORAS DE ARCHIVOS (Múltiples) */
    .pill-container {
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
        margin-left: 55px;
        margin-bottom: 8px;
    }

    .file-pill {
        background-color: #e8f0fe;
        color: #1a73e8;
        padding: 4px 12px;
        border-radius: 12px;
        font-size: 0.82rem;
        border: 1px solid #c2e7ff;
        display: flex;
        align-items: center;
        gap: 5px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. LÓGICA DE ESTADOS ---
if "chats" not in st.session_state:
    st.session_state.chats = {"Chat 1": []}
if "current_chat" not in st.session_state:
    st.session_state.current_chat = "Chat 1"

client = Groq(api_key=st.secrets["GROQ_API_KEY"])

# --- 3. PROCESADOR DE ARCHIVOS MÚLTIPLES ---
def procesar_archivos(lista_archivos):
    contexto_total = ""
    imagenes_b64 = [] # Groq Vision soporta múltiples imágenes en una llamada
    
    for archivo in lista_archivos:
        try:
            if "image" in archivo.type:
                b64 = base64.b64encode(archivo.read()).decode()
                imagenes_b64.append(f"data:{archivo.type};base64,{b64}")
            elif "pdf" in archivo.type:
                reader = PyPDF2.PdfReader(archivo)
                contexto_total += f"\n[Archivo: {archivo.name}]\n" + " ".join([p.extract_text() for p in reader.pages])
            else:
                contexto_total += f"\n[Archivo: {archivo.name}]\n" + archivo.read().decode()
        except:
            pass
    return contexto_total, imagenes_b64

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
        if st.button(c, key=f"n_{c}", use_container_width=True):
            st.session_state.current_chat = c
            st.rerun()

# --- 5. RENDER CHAT ---
st.subheader(st.session_state.current_chat)
history = st.session_state.chats[st.session_state.current_chat]

for m in history:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

# --- 6. BARRA INFERIOR MULTI-ARCHIVO ---
with st.container():
    # accept_multiple_files=True permite la carga masiva
    archivos = st.file_uploader("", type=["pdf", "png", "jpg", "txt", "csv"], 
                                 label_visibility="collapsed", accept_multiple_files=True)
    
    if archivos:
        st.markdown('<div class="pill-container">', unsafe_allow_html=True)
        for f in archivos:
            st.markdown(f'<div class="file-pill">📄 {f.name}</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    
    prompt = st.chat_input("Escribe tu mensaje...")

# --- 7. LÓGICA DE RESPUESTA ---
if prompt:
    history.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    contexto_texto, lista_imgs = procesar_archivos(archivos)

    with st.chat_message("assistant"):
        placeholder = st.empty()
        full_res = ""
        
        # Si hay imágenes, usamos el modelo Vision
        if lista_imgs:
            modelo = "llama-3.2-11b-vision-preview"
            contenido_multi = [{"type": "text", "text": f"{contexto_texto}\n\n{prompt}"}]
            for img in lista_imgs:
                contenido_multi.append({"type": "image_url", "image_url": {"url": img}})
            msgs = [{"role": "user", "content": contenido_multi}]
        else:
            modelo = "llama-3.3-70b-versatile"
            msgs = [{"role": "user", "content": f"{contexto_texto}\n\n{prompt}"}]

        try:
            completion = client.chat.completions.create(model=modelo, messages=msgs, stream=True)
            for chunk in completion:
                if chunk.choices[0].delta.content:
                    full_res += chunk.choices[0].delta.content
                    placeholder.markdown(full_res + "▌")
            placeholder.markdown(full_res)
            history.append({"role": "assistant", "content": full_res})
            st.rerun()
        except Exception as e:
            st.error(f"Error de conexión: {e}")
