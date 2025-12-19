import streamlit as st
from groq import Groq
import base64
import PyPDF2
from datetime import datetime

# --- 1. CONFIGURACIÓN Y CSS (LIMPIEZA TOTAL) ---
st.set_page_config(page_title="Gemini", page_icon="✨", layout="wide")

st.markdown("""
    <style>
    header, footer {visibility: hidden;}
    
    /* Centrar el chat */
    .main .block-container { max-width: 900px; padding-bottom: 150px; }

    /* OCULTAR TEXTOS DEL CARGADOR */
    [data-testid="stFileUploader"] section { padding: 0 !important; min-height: 0 !important; border: none !important; }
    [data-testid="stFileUploader"] label, [data-testid="stFileUploader"] small, 
    [data-testid="stFileUploader"] div, [data-testid="stFileUploaderDropzoneInstructions"] { 
        display: none !important; 
    }
    
    /* Botón del clip circular */
    [data-testid="stFileUploader"] button {
        border: none !important;
        background-color: #f0f2f6 !important;
        border-radius: 50% !important;
        color: transparent !important;
        width: 45px !important;
        height: 45px !important;
    }
    [data-testid="stFileUploader"] button::after {
        content: '📎';
        color: #444746;
        font-size: 22px;
        position: absolute;
        top: 50%; left: 50%;
        transform: translate(-50%, -50%);
    }

    /* Fijar la barra de entrada al fondo */
    .footer-container {
        position: fixed;
        bottom: 0;
        left: 0;
        right: 0;
        background: white;
        padding: 20px 15%;
        z-index: 999;
    }

    /* Estilo de la píldora de archivo */
    .file-pill {
        background-color: #e8f0fe;
        color: #1a73e8;
        padding: 5px 15px;
        border-radius: 20px;
        font-size: 0.9rem;
        border: 1px solid #1a73e8;
        margin-bottom: 10px;
        display: inline-block;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. GESTIÓN DE CHATS ---
if "chats" not in st.session_state:
    st.session_state.chats = {"Chat 1": []}
if "current_chat" not in st.session_state:
    st.session_state.current_chat = "Chat 1"

client = Groq(api_key=st.secrets["GROQ_API_KEY"])

# --- 3. PROCESADOR DE ARCHIVOS ---
def procesar_archivo(file):
    if not file: return None, None
    if "image" in file.type:
        return "image", f"data:{file.type};base64,{base64.b64encode(file.read()).decode()}"
    if "pdf" in file.type:
        reader = PyPDF2.PdfReader(file)
        return "text", "INFO PDF: " + " ".join([p.extract_text() for p in reader.pages])
    return "text", file.read().decode()

# --- 4. SIDEBAR (HISTORIAL) ---
with st.sidebar:
    st.title("✨ Gemini")
    if st.button("➕ Nuevo chat", use_container_width=True):
        nuevo = f"Chat {len(st.session_state.chats) + 1}"
        st.session_state.chats[nuevo] = []
        st.session_state.current_chat = nuevo
        st.rerun()
    st.divider()
    for c_id in reversed(list(st.session_state.chats.keys())):
        if st.button(c_id, key=f"nav_{c_id}", use_container_width=True):
            st.session_state.current_chat = c_id
            st.rerun()

# --- 5. VISTA DE CHAT ---
st.subheader(st.session_state.current_chat)
history = st.session_state.chats[st.session_state.current_chat]

for m in history:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

# --- 6. BARRA INFERIOR (CONTENEDOR FIJO) ---
st.write("<div style='height: 100px;'></div>", unsafe_allow_html=True)

# Creamos la barra de entrada usando columnas reales para alineación perfecta
with st.container():
    # Mostrar píldora si hay archivo antes del chat_input
    col_main = st.columns([1])[0]
    
    with st.sidebar: # Truco para el file uploader: ponerlo en un sitio donde no estorbe pero se procese
        archivo = st.file_uploader("Subir", type=["pdf", "png", "jpg", "txt"], label_visibility="collapsed")

    # Layout de la barra inferior
    c1, c2 = st.columns([0.07, 0.93])
    
    with c1:
        # Aquí movemos el botón del uploader al sitio del clip mediante CSS
        st.write(" ") # Espaciador
        # El CSS arriba ya se encarga de que st.file_uploader se vea como un clip 
        # Pero lo llamamos aquí para que aparezca junto a la barra
        archivo = st.file_uploader("", type=["pdf", "png", "jpg", "txt"], key="footer_upload", label_visibility="collapsed")

    with c2:
        if archivo:
            st.markdown(f'<div class="file-pill">📄 {archivo.name}</div>', unsafe_allow_html=True)
        prompt = st.chat_input("Escribe tu mensaje...")

# --- 7. LÓGICA DE RESPUESTA ---
if prompt:
    history.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    tipo, contenido = procesar_archivo(archivo)

    with st.chat_message("assistant"):
        modelo = "llama-3.2-11b-vision-preview" if tipo == "image" else "llama-3.3-70b-versatile"
        
        if tipo == "image":
            msgs = [{"role": "user", "content": [{"type": "text", "text": prompt}, {"type": "image_url", "image_url": {"url": contenido}}]}]
        else:
            ctx = f"ARCHIVO ADJUNTO: {contenido}\n\n" if contenido else ""
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
