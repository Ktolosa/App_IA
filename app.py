import streamlit as st
from groq import Groq
import base64
import PyPDF2

# --- 1. CONFIGURACIÓN Y CSS (ALINEACIÓN IZQUIERDA ABSOLUTA) ---
st.set_page_config(page_title="Gemini Ultra", page_icon="✨", layout="wide")

st.markdown("""
    <style>
    header, footer {visibility: hidden;}
    .main .block-container { max-width: 850px; padding-bottom: 150px; }

    /* CONTENEDOR DE ENTRADA FIJO */
    .stChatFloatingInputContainer {
        bottom: 30px !important;
        background-color: transparent !important;
    }

    /* POSICIONAR EL CARGADOR DENTRO DE LA BARRA A LA IZQUIERDA */
    [data-testid="stFileUploader"] {
        position: absolute;
        left: 20px; /* Distancia desde el borde izquierdo */
        top: 10px;  /* Ajuste para centrar verticalmente con el texto */
        width: 40px;
        z-index: 1000;
    }
    
    /* Eliminar todos los textos y marcos del cargador */
    [data-testid="stFileUploader"] section { padding: 0 !important; min-height: 0 !important; border: none !important; background: transparent !important; }
    [data-testid="stFileUploader"] label, [data-testid="stFileUploader"] small, 
    [data-testid="stFileUploader"] div, [data-testid="stFileUploaderDropzoneInstructions"] { 
        display: none !important; 
    }

    /* Convertir el botón en el círculo con el clip */
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

    /* ESTILO DE LA BARRA DE TEXTO (GEMINI STYLE) */
    .stChatInput textarea {
        border-radius: 28px !important;
        background-color: #f0f2f6 !important;
        border: none !important;
        padding-left: 55px !important; /* IMPORTANTE: Espacio para que el texto no tape el clip */
        padding-top: 12px !important;
    }

    /* Píldora de archivo (Estilo flotante sobre la barra) */
    .file-pill {
        background-color: #e8f0fe;
        color: #1a73e8;
        padding: 4px 12px;
        border-radius: 12px;
        font-size: 0.85rem;
        margin-left: 55px;
        margin-bottom: 8px;
        border: 1px solid #c2e7ff;
        display: inline-block;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. LÓGICA DE ESTADOS ---
if "chats" not in st.session_state:
    st.session_state.chats = {"Chat 1": []}
if "current_chat" not in st.session_state:
    st.session_state.current_chat = "Chat 1"

client = Groq(api_key=st.secrets["GROQ_API_KEY"])

# --- 3. BARRA LATERAL ---
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

# --- 4. RENDERIZADO DE CHAT ---
st.subheader(st.session_state.current_chat)
history = st.session_state.chats[st.session_state.current_chat]

for m in history:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

# --- 5. BARRA INFERIOR ( CLIP + INPUT ) ---
with st.container():
    # El archivo subido
    archivo = st.file_uploader("", type=["pdf", "png", "jpg", "txt", "csv"], label_visibility="collapsed")
    
    if archivo:
        st.markdown(f'<div class="file-pill">📄 {archivo.name}</div>', unsafe_allow_html=True)
    
    prompt = st.chat_input("Escribe tu mensaje...")

# --- 6. PROCESAMIENTO ---
if prompt:
    history.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Extraer contenido del archivo
    contexto = ""
    img_b64 = None
    if archivo:
        if "image" in archivo.type:
            img_b64 = f"data:{archivo.type};base64,{base64.b64encode(archivo.read()).decode()}"
        elif "pdf" in archivo.type:
            reader = PyPDF2.PdfReader(archivo)
            contexto = "Contenido PDF: " + " ".join([p.extract_text() for p in reader.pages])
        else:
            contexto = f"Contenido del archivo: {archivo.read().decode()}"

    with st.chat_message("assistant"):
        placeholder = st.empty()
        full_res = ""
        modelo = "llama-3.2-11b-vision-preview" if img_b64 else "llama-3.3-70b-versatile"
        
        # Preparar mensajes
        if img_b64:
            msgs = [{"role": "user", "content": [{"type":"text","text":prompt}, {"type":"image_url","image_url":{"url":img_b64}}]}]
        else:
            msgs = [{"role": "user", "content": f"{contexto}\n\n{prompt}"}]

        completion = client.chat.completions.create(model=modelo, messages=msgs, stream=True)
        for chunk in completion:
            if chunk.choices[0].delta.content:
                full_res += chunk.choices[0].delta.content
                placeholder.markdown(full_res + "▌")
        
        placeholder.markdown(full_res)
        history.append({"role": "assistant", "content": full_res})
        st.rerun()
