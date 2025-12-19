import streamlit as st
from groq import Groq
import base64
import PyPDF2
import io
from datetime import datetime

# --- 1. CONFIGURACIÓN Y CSS (ESTILO GEMINI PIXEL-PERFECT) ---
st.set_page_config(page_title="Gemini Pro", page_icon="✨", layout="wide")

st.markdown("""
    <style>
    header, footer {visibility: hidden;}
    .main .block-container { max-width: 850px; padding-bottom: 150px; }
    
    /* Barra inferior fija */
    .stChatFloatingInputContainer { bottom: 30px !important; background-color: transparent !important; }
    
    /* Ocultar textos del cargador y dejar solo el clip */
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

# --- 2. INICIALIZACIÓN DE ESTADOS ---
if "chats" not in st.session_state:
    st.session_state.chats = {"Chat 1": []}
if "current_chat" not in st.session_state:
    st.session_state.current_chat = "Chat 1"

client = Groq(api_key=st.secrets["GROQ_API_KEY"])

# --- 3. PROCESADOR DE ARCHIVOS ---
def extraer_contenido(archivo):
    if archivo is None: return None, None
    try:
        if "image" in archivo.type:
            return "image", f"data:{archivo.type};base64,{base64.b64encode(archivo.read()).decode()}"
        elif "pdf" in archivo.type:
            pdf_reader = PyPDF2.PdfReader(archivo)
            texto = "CONTENIDO DEL PDF ADJUNTO:\n" + "\n".join([p.extract_text() for p in pdf_reader.pages])
            return "text", texto
        elif "audio" in archivo.type:
            transcription = client.audio.transcriptions.create(file=(archivo.name, archivo.read()), model="whisper-large-v3")
            return "text", f"TRANSCRIPCIÓN DEL AUDIO ADJUNTO: {transcription.text}"
        else:
            return "text", f"CONTENIDO DEL ARCHIVO: {archivo.read().decode()}"
    except Exception as e:
        return "error", str(e)

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
mensajes = st.session_state.chats[st.session_state.current_chat]
for m in mensajes:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

# --- 6. INPUT Y RESPUESTA ---
with st.container():
    archivo_adjunto = st.file_uploader("", type=["pdf", "png", "jpg", "mp3", "wav", "txt", "csv"], label_visibility="collapsed")
    prompt = st.chat_input("Escribe tu mensaje aquí...")

if prompt:
    # Agregar mensaje usuario
    mensajes.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Procesar el archivo ANTES de llamar a la IA
    tipo, contenido = extraer_contenido(archivo_adjunto)

    with st.chat_message("assistant"):
        placeholder = st.empty()
        full_res = ""
        
        # Lógica de mensajes para la API
        if tipo == "image":
            modelo = "llama-3.2-11b-vision-preview"
            payload = [
                {"role": "system", "content": "Eres Gemini. Analiza la imagen enviada."},
                {"role": "user", "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": contenido}}
                ]}
            ]
        else:
            modelo = "llama-3.3-70b-versatile"
            contexto = f"{contenido}\n\n" if contenido else ""
            payload = [
                {"role": "system", "content": "Eres Gemini. Usa el contenido del archivo si existe."},
                {"role": "user", "content": f"{contexto}Pregunta: {prompt}"}
            ]

        # Llamada a Groq
        try:
            stream = client.chat.completions.create(model=modelo, messages=payload, stream=True)
            for chunk in stream:
                if chunk.choices[0].delta.content:
                    full_res += chunk.choices[0].delta.content
                    placeholder.markdown(full_res + "▌")
            placeholder.markdown(full_res)
            mensajes.append({"role": "assistant", "content": full_res})
        except Exception as e:
            st.error(f"Error: {e}")
