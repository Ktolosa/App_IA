import streamlit as st
from groq import Groq
from datetime import datetime
import PyPDF2
import base64
import pandas as pd
import io

# 1. Configuración de página y Estilo
st.set_page_config(page_title="Ultra IA Multimodal", page_icon="⚡", layout="wide")

st.markdown("""
    <style>
    .stChatFloatingInputContainer { bottom: 20px; }
    .st-emotion-cache-1c7n2ka { max-width: 95%; }
    </style>
    """, unsafe_allow_html=True)

# 2. Inicialización y Seguridad
try:
    client = Groq(api_key=st.secrets["GROQ_API_KEY"])
except:
    st.error("⚠️ Configura la GROQ_API_KEY en los Secrets de Streamlit.")
    st.stop()

if "messages" not in st.session_state:
    st.session_state.messages = []

# 3. Sidebar y Herramientas
with st.sidebar:
    st.title("⚙️ Panel de Control")
    uploaded_file = st.file_uploader("Cargar archivos (PDF, Imagen, Audio, CSV, Excel)", 
                                    type=["pdf", "png", "jpg", "jpeg", "mp3", "wav", "csv", "xlsx"])
    if st.button("🗑️ Limpiar Chat"):
        st.session_state.messages = []
        st.rerun()

# 4. Procesamiento de Archivos (Detección Inteligente)
contexto_archivo = ""
image_content = None

if uploaded_file:
    with st.status("Procesando archivo..."):
        if uploaded_file.type in ["image/png", "image/jpeg"]:
            base64_image = base64.b64encode(uploaded_file.read()).decode('utf-8')
            image_content = f"data:{uploaded_file.type};base64,{base64_image}"
            contexto_archivo = "[Imagen cargada lista para análisis visual]"
        
        elif uploaded_file.type == "application/pdf":
            pdf_reader = PyPDF2.PdfReader(uploaded_file)
            texto = " ".join([p.extract_text() for p in pdf_reader.pages])
            contexto_archivo = f"\n[CONTENIDO PDF]: {texto[:10000]}" # Límite para evitar errores
            
        elif "audio" in uploaded_file.type:
            transcription = client.audio.transcriptions.create(
                file=(uploaded_file.name, uploaded_file.read()),
                model="whisper-large-v3"
            )
            contexto_archivo = f"\n[TRANSCRIPCIÓN AUDIO]: {transcription.text}"
            
        elif uploaded_file.name.endswith(('.csv', '.xlsx')):
            df = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
            st.dataframe(df.head(10))
            contexto_archivo = f"\n[DATOS TABULARES (Primeras filas)]: {df.head(5).to_string()}"

# 5. Visualización del Chat
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# 6. Entrada de Usuario y Lógica IA
if prompt := st.chat_input("Escribe aquí o pregunta sobre el archivo..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        # Selección de modelo
        model_to_use = "llama-3.2-11b-vision-preview" if image_content else "llama-3.3-70b-versatile"
        
        # System Prompt con superpoderes
        sys_msg = f"""Eres una IA avanzada. Hoy es {datetime.now().strftime('%Y-%m-%d')}.
        Capacidades actuales:
        - Si hay datos, analízalos.
        - Si el usuario pide un PDF/Excel/Word, responde primero con texto y luego genera el contenido.
        - Si pide gráficos, usa tablas de markdown.
        Archivo actual: {contexto_archivo if contexto_archivo else 'Ninguno'}"""

        messages_api = [{"role": "system", "content": sys_msg}]
        
        if image_content:
            messages_api.append({
                "role": "user",
                "content": [{"type": "text", "text": prompt}, {"type": "image_url", "image_url": {"url": image_content}}]
            })
        else:
            for m in st.session_state.messages[-6:]: # Memoria de los últimos 6 mensajes
                messages_api.append({"role": m["role"], "content": m["content"]})

        # Generación con Streaming
        res_placeholder = st.empty()
        full_res = ""
        
        try:
            completion = client.chat.completions.create(model=model_to_use, messages=messages_api, stream=True)
            for chunk in completion:
                if chunk.choices[0].delta.content:
                    full_res += chunk.choices[0].delta.content
                    res_placeholder.markdown(full_res + "▌")
            res_placeholder.markdown(full_res)
            st.session_state.messages.append({"role": "assistant", "content": full_res})
            
            # --- FUNCIÓN ESPECIAL: GENERAR ARCHIVOS DESCARGABLES ---
            if "generar excel" in prompt.lower() or "bajar datos" in prompt.lower():
                df_download = pd.DataFrame([{"Resultado": "IA Gen", "Fecha": datetime.now()}] )
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                    df_download.to_excel(writer, index=False)
                st.download_button("📥 Descargar Excel Generado", data=output.getvalue(), file_name="analisis.xlsx")
                
        except Exception as e:
            st.error(f"Error: {e}")
