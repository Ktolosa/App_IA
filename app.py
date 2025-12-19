import streamlit as st
from groq import Groq
from datetime import datetime
import PyPDF2
import base64
import pandas as pd
import plotly.express as px
import io
from fpdf import FPDF
from docx import Document

# --- CONFIGURACIÓN E INTERFAZ ---
st.set_page_config(page_title="IA Multimodal Pro", page_icon="✨", layout="wide")

# CSS para ocultar etiquetas y ajustar el botón al lado del input
st.markdown("""
    <style>
    .stChatFloatingInputContainer { background-color: transparent !important; }
    div[data-testid="stColumn"] { display: flex; align-items: center; }
    .stFileUploader { padding-bottom: 0px; }
    </style>
    """, unsafe_allow_html=True)

# Inicializar Groq
if "messages" not in st.session_state:
    st.session_state.messages = []

try:
    client = Groq(api_key=st.secrets["GROQ_API_KEY"])
except:
    st.error("Configura GROQ_API_KEY en Secrets.")
    st.stop()

# --- FUNCIONES DE GENERACIÓN DE ARCHIVOS ---
def crear_pdf(texto):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.multi_cell(0, 10, txt=texto.encode('latin-1', 'replace').decode('latin-1'))
    return pdf.output(dest='S').encode('latin-1')

def crear_word(texto):
    doc = Document()
    doc.add_paragraph(texto)
    bio = io.BytesIO()
    doc.save(bio)
    return bio.getvalue()

# --- UI: CHAT HISTORIAL ---
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if "chart" in message:
            st.plotly_chart(message["chart"], use_container_width=True)
        if "file" in message:
            st.download_button(**message["file"])

# --- UI: BARRA DE ENTRADA (ESTILO GEMINI) ---
# Usamos un contenedor en la parte inferior
with st.container():
    c1, c2 = st.columns([0.1, 0.9])
    with c1:
        archivo_subido = st.file_uploader("📎", type=["pdf", "png", "jpg", "csv", "xlsx", "txt"], label_visibility="collapsed")
    with c2:
        prompt = st.chat_input("Escribe tu consulta o pide un gráfico/archivo...")

if prompt:
    # 1. Procesar contexto de archivos subidos
    contexto_archivo = ""
    img_b64 = None
    if archivo_subido:
        if "image" in archivo_subido.type:
            img_b64 = f"data:{archivo_subido.type};base64,{base64.b64encode(archivo_subido.read()).decode()}"
        elif "pdf" in archivo_subido.type:
            reader = PyPDF2.PdfReader(archivo_subido)
            contexto_archivo = "Contenido PDF: " + " ".join([p.extract_text() for p in reader.pages])
        elif "csv" in archivo_subido.type or "sheet" in archivo_subido.type:
            df_input = pd.read_csv(archivo_subido) if "csv" in archivo_subido.type else pd.read_excel(archivo_subido)
            contexto_archivo = f"Datos del archivo: {df_input.head(10).to_dict()}"

    # 2. Mostrar mensaje del usuario
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # 3. Respuesta de la IA
    with st.chat_message("assistant"):
        modelo = "llama-3.2-11b-vision-preview" if img_b64 else "llama-3.3-70b-versatile"
        
        sys_prompt = f"""Eres una IA avanzada. Hoy es {datetime.now()}. 
        Si te piden un gráfico, inventa datos coherentes si no hay, y responde SIEMPRE al final con el formato:
        [DATA: {{"Etiqueta1": 10, "Etiqueta2": 20}}]
        Si piden un archivo, responde normal y yo generaré el botón."""

        # Construir mensajes
        msgs = [{"role": "system", "content": sys_prompt}]
        if img_b64:
            msgs.append({"role": "user", "content": [{"type": "text", "text": prompt}, {"type": "image_url", "image_url": {"url": img_b64}}]})
        else:
            for m in st.session_state.messages[-5:]:
                msgs.append({"role": m["role"], "content": m["content"]})

        # Streaming
        placeholder = st.empty()
        full_res = ""
        completion = client.chat.completions.create(model=modelo, messages=msgs, stream=True)
        for chunk in completion:
            if chunk.choices[0].delta.content:
                full_res += chunk.choices[0].delta.content
                placeholder.markdown(full_res + "▌")
        placeholder.markdown(full_res)

        new_msg = {"role": "assistant", "content": full_res}

        # --- LÓGICA DE GRÁFICOS ---
        if "[DATA:" in full_res:
            try:
                import json
                data_str = full_res.split("[DATA:")[1].split("]")[0]
                data_json = json.loads(data_str)
                fig = px.pie(names=list(data_json.keys()), values=list(data_json.values()), title="Gráfico Generado")
                st.plotly_chart(fig)
                new_msg["chart"] = fig
            except: pass

        # --- LÓGICA DE ARCHIVOS ---
        p_low = prompt.lower()
        if "pdf" in p_low:
            new_msg["file"] = {"label": "📥 Descargar PDF", "data": crear_pdf(full_res), "file_name": "archivo.pdf", "mime": "application/pdf"}
        elif "word" in p_low or "docx" in p_low:
            new_msg["file"] = {"label": "📥 Descargar Word", "data": crear_word(full_res), "file_name": "archivo.docx", "mime": "application/vnd.openxmlformats-officedocument.wordprocessingml.document"}
        elif "excel" in p_low:
            df = pd.DataFrame([{"Contenido": full_res}])
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df.to_excel(writer, index=False)
            new_msg["file"] = {"label": "📥 Descargar Excel", "data": output.getvalue(), "file_name": "datos.xlsx", "mime": "application/vnd.ms-excel"}

        if "file" in new_msg:
            st.download_button(**new_msg["file"])
        
        st.session_state.messages.append(new_msg)
