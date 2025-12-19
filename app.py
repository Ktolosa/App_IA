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

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Gemini Ultra", page_icon="✨", layout="wide")

# --- CSS AVANZADO PARA INTERFAZ GEMINI ---
st.markdown("""
    <style>
    /* 1. Ocultar completamente los textos del cargador de archivos */
    [data-testid="stFileUploader"] section { padding: 0; min-height: 0; border: none; background: transparent; }
    [data-testid="stFileUploader"] label, [data-testid="stFileUploader"] small, 
    [data-testid="stFileUploader"] div[data-testid="stMarkdownContainer"] { display: none; }
    [data-testid="stFileUploader"] button { 
        border: none; background: #f0f2f6; border-radius: 50%; width: 40px; height: 40px;
    }

    /* 2. Anclar la barra de entrada al fondo */
    .stChatFloatingInputContainer {
        position: fixed;
        bottom: 30px;
        background-color: white !important;
        padding: 10px;
        z-index: 100;
    }

    /* 3. Estilo de los mensajes */
    .stChatMessage { border-radius: 20px; margin-bottom: 15px; max-width: 85%; }
    
    /* 4. Sidebar Estilizada */
    [data-testid="stSidebar"] { background-color: #f8f9fa; }
    </style>
    """, unsafe_allow_html=True)

# --- INICIALIZACIÓN DE CLIENTE Y ESTADOS ---
client = Groq(api_key=st.secrets["GROQ_API_KEY"])

if "all_chats" not in st.session_state:
    st.session_state.all_chats = {"Chat 1": []}
if "current_chat" not in st.session_state:
    st.session_state.current_chat = "Chat 1"

# --- SIDEBAR (HISTORIAL) ---
with st.sidebar:
    st.title("✨ Gemini")
    if st.button("➕ Nuevo Chat", use_container_width=True):
        new_id = f"Chat {len(st.session_state.all_chats) + 1}"
        st.session_state.all_chats[new_id] = []
        st.session_state.current_chat = new_id
        st.rerun()
    
    st.divider()
    for chat_id in reversed(list(st.session_state.all_chats.keys())):
        if st.button(chat_id, key=f"btn_{chat_id}"):
            st.session_state.current_chat = chat_id
            st.rerun()

# --- ÁREA DE CHAT (MENSAJES) ---
# Contenedor para que el chat no choque con la barra de abajo
chat_container = st.container()
with chat_container:
    st.subheader(st.session_state.current_chat)
    for msg in st.session_state.all_chats[st.session_state.current_chat]:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if "chart" in msg: st.plotly_chart(msg["chart"])
            if "file" in msg: st.download_button(**msg["file"])

# Espacio extra para que el último mensaje no quede detrás de la barra
st.markdown("<br><br><br><br><br><br>", unsafe_allow_html=True)

# --- BARRA INFERIOR (ENTRADA Y CARGA) ---
with st.container():
    # Usamos columnas dentro de un contenedor fijo por CSS
    col_file, col_txt = st.columns([0.07, 0.93])
    
    with col_file:
        # Solo se verá el botón de "Browse" que estilice con CSS para que parezca un icono
        archivo = st.file_uploader("📎", type=["pdf", "png", "jpg", "csv", "xlsx", "txt"], label_visibility="collapsed")
    
    with col_txt:
        prompt = st.chat_input("Escribe tu mensaje aquí...")

# --- LÓGICA DE PROCESAMIENTO ---
if prompt:
    contexto_archivo = ""
    img_b64 = None
    
    if archivo:
        if "image" in archivo.type:
            img_b64 = f"data:{archivo.type};base64,{base64.b64encode(archivo.read()).decode()}"
        elif "pdf" in archivo.type:
            reader = PyPDF2.PdfReader(archivo)
            contexto_archivo = "Contenido PDF: " + " ".join([p.extract_text() for p in reader.pages])

    # Guardar y mostrar mensaje del usuario
    st.session_state.all_chats[st.session_state.current_chat].append({"role": "user", "content": prompt})
    st.rerun() # Rerunning para asegurar el orden visual

# Si el último mensaje es del usuario, generar respuesta del asistente
messages = st.session_state.all_chats[st.session_state.current_chat]
if messages and messages[-1]["role"] == "user":
    with st.chat_message("assistant"):
        user_prompt = messages[-1]["content"]
        modelo = "llama-3.2-11b-vision-preview" if img_b64 else "llama-3.3-70b-versatile"
        
        sys_prompt = f"Eres Gemini. Fecha: {datetime.now()}. {contexto_archivo}. Si piden gráficos usa [DATA: {{\"Etiqueta\": valor}}]"
        
        api_msgs = [{"role": "system", "content": sys_prompt}]
        # Memoria corta (últimos 4 mensajes)
        for m in messages[-4:]:
            api_msgs.append({"role": m["role"], "content": m["content"]})

        full_res = ""
        placeholder = st.empty()
        
        completion = client.chat.completions.create(model=modelo, messages=api_msgs, stream=True)
        for chunk in completion:
            if chunk.choices[0].delta.content:
                full_res += chunk.choices[0].delta.content
                placeholder.markdown(full_res + "▌")
        placeholder.markdown(full_res)

        # Crear el objeto de mensaje
        new_msg = {"role": "assistant", "content": full_res}

        # Detección de gráficos
        if "[DATA:" in full_res:
            try:
                import json
                data_json = json.loads(full_res.split("[DATA:")[1].split("]")[0])
                fig = px.pie(names=list(data_json.keys()), values=list(data_json.values()), hole=0.4)
                st.plotly_chart(fig)
                new_msg["chart"] = fig
            except: pass

        # Detección de archivos
        p_low = user_prompt.lower()
        if "pdf" in p_low:
            pdf = FPDF(); pdf.add_page(); pdf.set_font("Arial", size=12)
            pdf.multi_cell(0, 10, txt=full_res.encode('latin-1', 'replace').decode('latin-1'))
            new_msg["file"] = {"label": "📥 Descargar PDF", "data": pdf.output(dest='S').encode('latin-1'), "file_name": "documento.pdf"}
        
        st.session_state.all_chats[st.session_state.current_chat].append(new_msg)
        st.rerun()
