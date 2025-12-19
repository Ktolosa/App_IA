import streamlit as st
from groq import Groq
from datetime import datetime
import PyPDF2
from PIL import Image
import io

# 1. Configuración de la App
st.set_page_config(page_title="Super IA Multimodal", page_icon="🚀", layout="wide")
st.title("🚀 Super IA: Lee todo")

# 2. Conexión segura con Groq
try:
    client = Groq(api_key=st.secrets["GROQ_API_KEY"])
except:
    st.error("Configura GROQ_API_KEY en Secrets.")
    st.stop()

# 3. Sidebar para carga de archivos
st.sidebar.header("📁 Carga de Archivos")
uploaded_file = st.sidebar.file_uploader(
    "Sube un archivo (PDF, Imagen, Audio, TXT)", 
    type=["pdf", "png", "jpg", "jpeg", "txt", "mp3", "m4a", "wav"]
)

contexto_archivo = ""

if uploaded_file:
    # --- PROCESAR PDF ---
    if uploaded_file.type == "application/pdf":
        pdf_reader = PyPDF2.PdfReader(uploaded_file)
        texto_pdf = ""
        for page in pdf_reader.pages:
            texto_pdf += page.extract_text()
        contexto_archivo = f"\n[Contenido del PDF cargado]:\n{texto_pdf}"
        st.sidebar.success("PDF procesado")

    # --- PROCESAR TEXTO ---
    elif uploaded_file.type == "text/plain":
        contexto_archivo = f"\n[Contenido del archivo TXT]:\n{uploaded_file.read().decode()}"
        st.sidebar.success("Texto procesado")

    # --- PROCESAR IMÁGENES (Vía Visión de Groq) ---
    elif uploaded_file.type in ["image/png", "image/jpeg"]:
        st.sidebar.image(uploaded_file, caption="Imagen cargada")
        # Nota: Aquí usamos el modelo de visión de Llama
        contexto_archivo = "\n[El usuario ha subido una imagen. Analízala si te preguntan por ella.]"
        # Para un análisis real de imagen, se enviaría el base64 a un modelo 'vision'

    # --- PROCESAR AUDIO (Transcripción con Whisper en Groq) ---
    elif "audio" in uploaded_file.type:
        st.sidebar.audio(uploaded_file)
        with st.spinner("Transcribiendo audio..."):
            transcription = client.audio.transcriptions.create(
                file=(uploaded_file.name, uploaded_file.read()),
                model="whisper-large-v3",
            )
            contexto_archivo = f"\n[Transcripción del audio subido]:\n{transcription.text}"
            st.sidebar.success("Audio transcrito")

# 4. Chat y Memoria
if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("¿Qué dice el archivo que subí?"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        # Instrucción Maestra
        system_prompt = f"""Eres una IA avanzada. Hoy es {datetime.now()}. 
        Si hay información abajo de este mensaje, es el contenido de un archivo que el usuario subió. 
        Úsalo para responder de forma experta.
        {contexto_archivo}"""

        full_history = [{"role": "system", "content": system_prompt}] + st.session_state.messages

        response_placeholder = st.empty()
        full_response = ""

        # Usamos Llama 3.3 70B para razonamiento profundo
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=full_history,
            stream=True
        )

        for chunk in completion:
            content = chunk.choices[0].delta.content
            if content:
                full_response += content
                response_placeholder.markdown(full_response + "▌")
        
        response_placeholder.markdown(full_response)
        st.session_state.messages.append({"role": "assistant", "content": full_response})
