import streamlit as st
from groq import Groq
import base64
import PyPDF2
import io
from datetime import datetime

# --- 1. CONFIGURACIÓN Y CSS (LIMPIEZA TOTAL) ---
st.set_page_config(page_title="Gemini Pro", page_icon="✨", layout="wide")

st.markdown("""
    <style>
    header, footer {visibility: hidden;}
    .stChatFloatingInputContainer { bottom: 30px !important; background-color: transparent !important; }
    [data-testid="stFileUploader"] { position: absolute; left: 10px; top: 10px; width: 42px; z-index: 100; }
    [data-testid="stFileUploader"] section { padding: 0 !important; min-height: 40px !important; border: none !important; }
    [data-testid="stFileUploader"] label, [data-testid="stFileUploader"] small, 
    [data-testid="stFileUploader"] div, [data-testid="stFileUploaderDropzoneInstructions"] { display: none !important; }
    [data-testid="stFileUploader"] button {
        width: 40px !important; height: 40px !important; border-radius: 50% !important;
        background-color: #f0f2f6 !important; color: transparent !important; border: none !important;
    }
    [data-testid="stFileUploader"]::before {
        content: '📎'; position: absolute; left: 10px; top: 8px; font-size: 20px; z-index: 101; pointer-events: none;
    }
    .stChatInput textarea { border-radius: 28px !important; padding-left: 55px !important; background-color: #f0f2f6 !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. INICIALIZACIÓN ---
if "chats" not in st.session_state:
    st.session_state.chats = {"Chat 1": []}
if "current_chat" not in st.session_state:
    st.session_state.current_chat = "Chat 1"

client = Groq(api_key=st.secrets["GROQ_API_KEY"])

# --- 3. PROCESAMIENTO DE ARCHIVOS ---
def procesar_archivo(file):
    if file is None: return None, None
    
    if "image" in file.type:
        b64_img = base64.b64encode(file.read()).decode()
        return "image", f"data:{file.type};base64,{b64_img}"
    
    elif "pdf" in file.type:
        pdf_reader = PyPDF2.PdfReader(file)
        texto = "Contenido del PDF:\n" + "".join([p.extract_text() for p in pdf_reader.pages])
        return "text", texto
    
    elif "audio" in file.type:
        transcription = client.audio.transcriptions.create(
            file=(file.name, file.read()),
            model="whisper-large-v3"
        )
        return "text", f"Transcripción de audio: {transcription.text}"
    
    return "text", file.read().decode()

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

# --- 5. CHAT UI ---
st.subheader(st.session_state.current_chat)
chat_actual = st.session_state.chats.get(st.session_state.current_chat, [])

for msg in chat_actual:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# --- 6. INPUT Y LÓGICA ---
with st.container():
    archivo = st.file_uploader("", type=["pdf", "png", "jpg", "mp3", "wav", "txt"], label_visibility="collapsed")
    prompt = st.chat_input("Escribe tu mensaje...")

if prompt:
    # 1. Mostrar mensaje del usuario inmediatamente
    chat_actual.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # 2. Procesar archivo si existe
    tipo_adjunto, contenido_adjunto = procesar_archivo(archivo)

    # 3. Respuesta de la IA
    with st.chat_message("assistant"):
        placeholder = st.empty()
        full_res = ""
        
        # Construir mensajes para la API
        mensajes_api = [{"role": "system", "content": "Eres Gemini. Si hay contexto de archivos, úsalo."}]
        
        # Si es imagen, usamos modelo Vision
        if tipo_adjunto == "image":
            modelo = "llama-3.2-11b-vision-preview"
            mensajes_api.append({
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": contenido_adjunto}}
                ]
            })
        else:
            modelo = "llama-3.3-70b-versatile"
            # Si hay texto de PDF/Audio, lo inyectamos
            texto_final = f"{contenido_adjunto}\n\nPregunta: {prompt}" if contenido_adjunto else prompt
            mensajes_api.append({"role": "user", "content": texto_final})

        # Streaming
        completion = client.chat.completions.create(model=modelo, messages=mensajes_api, stream=True)
        for chunk in completion:
            if chunk.choices[0].delta.content:
                full_res += chunk.choices[0].delta.content
                placeholder.markdown(full_res + "▌")
        
        placeholder.markdown(full_res)
        chat_actual.append({"role": "assistant", "content": full_res})
