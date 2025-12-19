import streamlit as st
from groq import Groq
from datetime import datetime
import PyPDF2
import base64

st.set_page_config(page_title="IA Multimodal Total", page_icon="👁️", layout="wide")
st.title("👁️ IA Multimodal: Ve, Escucha y Lee")

# Conexión a Groq
try:
    client = Groq(api_key=st.secrets["GROQ_API_KEY"])
except:
    st.error("Falta la GROQ_API_KEY en los Secrets.")
    st.stop()

# --- SIDEBAR: CARGA DE ARCHIVOS ---
st.sidebar.header("📁 Archivos")
uploaded_file = st.sidebar.file_uploader("Sube PDF, Imagen o Audio", type=["pdf", "png", "jpg", "jpeg", "mp3", "wav"])

contexto_adicional = ""
image_content = None

if uploaded_file:
    # 1. SI ES IMAGEN (VISIÓN)
    if uploaded_file.type in ["image/png", "image/jpeg"]:
        st.sidebar.image(uploaded_file, caption="Imagen lista para analizar")
        # Convertir imagen a Base64 para que la IA la vea
        base64_image = base64.b64encode(uploaded_file.read()).decode('utf-8')
        image_content = f"data:{uploaded_file.type};base64,{base64_image}"
        contexto_adicional = "(El usuario ha enviado una imagen)"

    # 2. SI ES PDF
    elif uploaded_file.type == "application/pdf":
        pdf_reader = PyPDF2.PdfReader(uploaded_file)
        texto = "".join([page.extract_text() for page in pdf_reader.pages])
        contexto_adicional = f"\n[TEXTO DEL PDF]: {texto}"
        st.sidebar.success("PDF leído")

    # 3. SI ES AUDIO
    elif "audio" in uploaded_file.type:
        with st.spinner("Escuchando audio..."):
            transcription = client.audio.transcriptions.create(
                file=(uploaded_file.name, uploaded_file.read()),
                model="whisper-large-v3"
            )
            contexto_adicional = f"\n[TRANSCRIPCIÓN DE AUDIO]: {transcription.text}"
            st.sidebar.success("Audio transcrito")

# --- CHAT ---
if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("¿Qué puedes decirme de esto?"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        # Selección automática de modelo: 
        # Si hay imagen usamos el modelo VISION, si no, el modelo 70B (más potente)
        model_to_use = "llama-3.2-11b-vision-preview" if image_content else "llama-3.3-70b-versatile"
        
        # Construir el mensaje para la API
        messages_api = [
            {"role": "system", "content": f"Eres una IA experta. Hoy es {datetime.now().strftime('%d/%m/%Y')}. {contexto_adicional}"}
        ]
        
        # Si hay imagen, el formato del mensaje cambia un poco
        if image_content:
            messages_api.append({
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": image_content}}
                ]
            })
        else:
            for m in st.session_state.messages:
                messages_api.append({"role": m["role"], "content": m["content"]})

        # Generar respuesta
        response_placeholder = st.empty()
        full_response = ""
        
        completion = client.chat.completions.create(
            model=model_to_use,
            messages=messages_api,
            stream=True
        )

        for chunk in completion:
            if chunk.choices[0].delta.content:
                full_response += chunk.choices[0].delta.content
                response_placeholder.markdown(full_response + "▌")
        
        response_placeholder.markdown(full_response)
        st.session_state.messages.append({"role": "assistant", "content": full_response})
