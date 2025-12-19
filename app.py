import streamlit as st
from groq import Groq
import base64
import PyPDF2

# --- 1. CONFIGURACIÓN Y CSS (ALINEACIÓN GEMINI) ---
st.set_page_config(page_title="Gemini Pro", page_icon="✨", layout="wide")

st.markdown("""
    <style>
    header, footer {visibility: hidden;}
    .main .block-container { max-width: 850px; padding-bottom: 180px; }

    /* Contenedor de la barra inferior */
    .stChatFloatingInputContainer {
        bottom: 20px !important;
        background-color: white !important;
        padding: 10px 0 !important;
    }

    /* POSICIONAMIENTO DEL CLIP A LA IZQUIERDA */
    [data-testid="stFileUploader"] {
        width: 45px;
        position: absolute;
        left: -50px; /* Lo mueve fuera del área de texto a la izquierda */
        top: 5px;
        z-index: 100;
    }
    
    [data-testid="stFileUploader"] section { padding: 0 !important; min-height: 0 !important; border: none !important; }
    [data-testid="stFileUploader"] label, [data-testid="stFileUploader"] small, 
    [data-testid="stFileUploader"] div, [data-testid="stMarkdownContainer"] { display: none !important; }
    
    [data-testid="stFileUploader"] button {
        background: #f0f2f6 !important;
        border-radius: 50% !important;
        width: 40px !important;
        height: 40px !important;
        color: transparent !important;
        border: none !important;
    }
    [data-testid="stFileUploader"] button::after {
        content: '📎';
        color: #444746;
        font-size: 20px;
        visibility: visible;
        position: absolute;
        left: 10px; top: 6px;
    }

    /* AJUSTE DE LA BARRA DE TEXTO */
    .stChatInput {
        margin-left: 50px !important; /* Deja espacio para el clip a la izquierda */
    }

    .stChatInput textarea {
        border-radius: 24px !important;
        background-color: #f0f2f6 !important;
        border: none !important;
    }

    /* Píldora de archivo (Encima de la barra) */
    .file-pill {
        display: flex;
        align-items: center;
        background-color: #e8f0fe;
        padding: 8px 16px;
        border-radius: 20px;
        margin-left: 50px;
        margin-bottom: 12px;
        width: fit-content;
        border: 1px solid #1a73e8;
        color: #1a73e8;
        font-weight: 500;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. LÓGICA DE DATOS ---
if "chats" not in st.session_state:
    st.session_state.chats = {"Chat 1": []}
if "current_chat" not in st.session_state:
    st.session_state.current_chat = "Chat 1"

client = Groq(api_key=st.secrets["GROQ_API_KEY"])

# --- 3. PROCESAMIENTO ---
def get_file_content(file):
    if file is None: return None, None
    if "image" in file.type:
        return "image", f"data:{file.type};base64,{base64.b64encode(file.read()).decode()}"
    elif "pdf" in file.type:
        reader = PyPDF2.PdfReader(file)
        return "text", "INFO PDF: " + " ".join([p.extract_text() for p in reader.pages])
    return "text", file.read().decode()

# --- 4. SIDEBAR ---
with st.sidebar:
    st.markdown("### ✨ Gemini")
    if st.button("➕ Nuevo chat", use_container_width=True):
        id = f"Chat {len(st.session_state.chats) + 1}"
        st.session_state.chats[id] = []
        st.session_state.current_chat = id
        st.rerun()
    st.divider()
    for c in reversed(list(st.session_state.chats.keys())):
        if st.button(c, key=f"nav_{c}", use_container_width=True):
            st.session_state.current_chat = c
            st.rerun()

# --- 5. CHAT VIEW ---
st.subheader(st.session_state.current_chat)
current_history = st.session_state.chats[st.session_state.current_chat]

for m in current_history:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

# --- 6. BARRA INFERIOR REORGANIZADA ---
with st.container():
    # El archivo subido se muestra arriba de la barra
    archivo = st.file_uploader("", type=["pdf", "png", "jpg", "txt"], label_visibility="collapsed")
    
    if archivo:
        st.markdown(f'<div class="file-pill">📄 {archivo.name}</div>', unsafe_allow_html=True)
    
    prompt = st.chat_input("Escribe tu mensaje...")

# --- 7. RESPUESTA ---
if prompt:
    current_history.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    tipo, contenido = get_file_content(archivo)

    with st.chat_message("assistant"):
        placeholder = st.empty()
        full_res = ""
        
        modelo = "llama-3.2-11b-vision-preview" if tipo == "image" else "llama-3.3-70b-versatile"
        
        # Construir mensajes
        if tipo == "image":
            msgs = [{"role": "user", "content": [{"type":"text","text":prompt}, {"type":"image_url","image_url":{"url":contenido}}]}]
        else:
            ctx = f"ARCHIVO: {contenido}\n\n" if contenido else ""
            msgs = [{"role": "user", "content": f"{ctx}{prompt}"}]

        stream = client.chat.completions.create(model=modelo, messages=msgs, stream=True)
        for chunk in stream:
            if chunk.choices[0].delta.content:
                full_res += chunk.choices[0].delta.content
                placeholder.markdown(full_res + "▌")
        
        placeholder.markdown(full_res)
        current_history.append({"role": "assistant", "content": full_res})
