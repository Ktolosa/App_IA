import streamlit as st
from groq import Groq
import base64
import PyPDF2
from datetime import datetime

# --- 1. CONFIGURACIÓN Y CSS (DISEÑO GEMINI TOTAL) ---
st.set_page_config(page_title="Gemini Ultra", page_icon="✨", layout="wide")

st.markdown("""
    <style>
    /* Ocultar elementos de Streamlit */
    header, footer {visibility: hidden;}
    .main .block-container { max-width: 850px; padding-bottom: 180px; }

    /* CONTENEDOR DE ENTRADA FIJO AL FONDO */
    .stChatFloatingInputContainer {
        bottom: 30px !important;
        background-color: white !important;
        padding: 10px 0 !important;
    }

    /* ALINEACIÓN EN LÍNEA: CLIP + BARRA */
    [data-testid="stForm"] {
        display: flex !important;
        flex-direction: row !important;
        align-items: center !important;
        gap: 10px !important;
        border: none !important;
    }

    /* LIMPIEZA ABSOLUTA DEL CARGADOR */
    [data-testid="stFileUploader"] {
        width: 45px !important;
        margin-bottom: 0px !important;
    }
    
    [data-testid="stFileUploader"] section { padding: 0 !important; min-height: 0 !important; border: none !important; background: transparent !important; }
    [data-testid="stFileUploader"] label, [data-testid="stFileUploader"] small, 
    [data-testid="stFileUploader"] div, [data-testid="stFileUploaderDropzoneInstructions"] { 
        display: none !important; 
    }

    /* BOTÓN CIRCULAR CON CLIP (SIN TEXTO) */
    [data-testid="stFileUploader"] button {
        background-color: #f0f2f6 !important;
        color: transparent !important;
        border: none !important;
        width: 44px !important;
        height: 44px !important;
        border-radius: 50% !important;
        position: relative;
    }
    
    [data-testid="stFileUploader"] button::after {
        content: '📎';
        color: #444746;
        font-size: 22px;
        position: absolute;
        top: 50%; left: 50%;
        transform: translate(-50%, -50%);
        visibility: visible;
    }

    /* BARRA DE TEXTO ESTILO GEMINI */
    .stChatInput { flex-grow: 1 !important; }
    .stChatInput textarea {
        border-radius: 24px !important;
        background-color: #f0f2f6 !important;
        border: none !important;
        padding-top: 12px !important;
    }

    /* CONTENEDOR DE ARCHIVOS CARGADOS (MULTIPÍLDORAS) */
    .pill-container {
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
        margin-bottom: 10px;
        padding-left: 55px;
    }
    .file-pill {
        background-color: #e8f0fe;
        color: #1a73e8;
        padding: 4px 12px;
        border-radius: 15px;
        font-size: 0.85rem;
        border: 1px solid #c2e7ff;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. GESTIÓN DE ESTADOS Y CHATS ---
if "chats" not in st.session_state:
    st.session_state.chats = {"Chat 1": []}
if "current_chat" not in st.session_state:
    st.session_state.current_chat = "Chat 1"

# Configuración de Cliente
try:
    client = Groq(api_key=st.secrets["GROQ_API_KEY"])
except:
    st.error("Error: Configura tu API Key en los Secrets de Streamlit.")
    st.stop()

# --- 3. PROCESAMIENTO MULTI-ARCHIVO ---
def procesar_archivos_input(archivos_subidos):
    text_ctx = ""
    img_list = []
    for f in archivos_subidos:
        if "image" in f.type:
            b64_data = base64.b64encode(f.read()).decode()
            img_list.append(f"data:{f.type};base64,{b64_data}")
        elif "pdf" in f.type:
            reader = PyPDF2.PdfReader(f)
            text_ctx += f"\n[Archivo: {f.name}]\n" + " ".join([p.extract_text() for p in reader.pages])
        else:
            text_ctx += f"\n[Archivo: {f.name}]\n" + f.read().decode()
    return text_ctx, img_list

# --- 4. SIDEBAR (HISTORIAL) ---
with st.sidebar:
    st.title("✨ Gemini")
    if st.button("➕ Nuevo chat", use_container_width=True):
        nuevo_nombre = f"Chat {len(st.session_state.chats) + 1}"
        st.session_state.chats[nuevo_nombre] = []
        st.session_state.current_chat = nuevo_nombre
        st.rerun()
    st.divider()
    for c_id in reversed(list(st.session_state.chats.keys())):
        if st.button(c_id, key=f"nav_{c_id}", use_container_width=True):
            st.session_state.current_chat = c_id
            st.rerun()

# --- 5. VISUALIZACIÓN DE CHAT ---
st.subheader(st.session_state.current_chat)
history = st.session_state.chats[st.session_state.current_chat]

for msg in history:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# --- 6. BARRA INFERIOR (CLIP + INPUT) ---
with st.container():
    # El cargador permite múltiples archivos y el CSS lo convierte en un clip
    archivos = st.file_uploader("", type=["pdf", "png", "jpg", "txt", "csv"], 
                                 accept_multiple_files=True, label_visibility="collapsed")
    
    if archivos:
        st.markdown('<div class="pill-container">', unsafe_allow_html=True)
        for f in archivos:
            st.markdown(f'<div class="file-pill">📄 {f.name}</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    
    prompt = st.chat_input("Escribe tu consulta aquí...")

# --- 7. LÓGICA DE RESPUESTA ---
if prompt:
    history.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    contexto_texto, lista_imagenes = procesar_archivos_input(archivos)

    with st.chat_message("assistant"):
        placeholder = st.empty()
        full_res = ""
        
        # Selección de Modelo (Actualizado a llama-3.2-11b-vision-preview)
        if lista_imagenes:
            model_name = "llama-3.2-11b-vision-preview"
            content_payload = [{"type": "text", "text": f"{contexto_texto}\n\n{prompt}"}]
            for img in lista_imagenes:
                content_payload.append({"type": "image_url", "image_url": {"url": img}})
            messages_payload = [{"role": "user", "content": content_payload}]
        else:
            model_name = "llama-3.3-70b-versatile"
            messages_payload = [{"role": "user", "content": f"{contexto_texto}\n\n{prompt}"}]

        try:
            completion = client.chat.completions.create(model=model_name, messages=messages_payload, stream=True)
            for chunk in completion:
                if chunk.choices[0].delta.content:
                    full_res += chunk.choices[0].delta.content
                    placeholder.markdown(full_res + "▌")
            placeholder.markdown(full_res)
            history.append({"role": "assistant", "content": full_res})
            st.rerun()
        except Exception as e:
            st.error(f"Error al conectar con Groq: {e}")
