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

# --- CONFIGURACIÓN E INTERFAZ ESTILO GEMINI ---
st.set_page_config(page_title="Gemini Ultra Pro", page_icon="✨", layout="wide")

# CSS para limpiar el file uploader y estilizar el chat
st.markdown("""
    <style>
    /* Ocultar textos del cargador de archivos para dejar solo el clip */
    section[data-testid="stFileUploader"] section { padding: 0; min-height: 0; border: none; }
    section[data-testid="stFileUploader"] label, 
    section[data-testid="stFileUploader"] small { display: none; }
    
    /* Ajuste de la barra inferior */
    .stChatFloatingInputContainer { 
        padding-bottom: 20px; 
        background-color: transparent !important; 
    }
    
    /* Contenedor principal centrado */
    .block-container { max-width: 900px; padding-top: 2rem; }
    
    /* Estilo para los botones del historial */
    .stButton>button {
        width: 100%;
        text-align: left;
        border: none;
        background: transparent;
        padding: 10px;
        border-radius: 10px;
    }
    .stButton>button:hover { background-color: #e0e0e0; }
    </style>
    """, unsafe_allow_html=True)

# --- GESTIÓN DE ESTADOS (MEMORIA Y CHATS) ---
if "all_chats" not in st.session_state:
    st.session_state.all_chats = {} # Diccionario para guardar múltiples chats
if "current_chat_id" not in st.session_state:
    st.session_state.current_chat_id = "Chat 1"
if st.session_state.current_chat_id not in st.session_state.all_chats:
    st.session_state.all_chats[st.session_state.current_chat_id] = []

client = Groq(api_key=st.secrets["GROQ_API_KEY"])

# --- BARRA LATERAL (HISTORIAL Y NUEVO CHAT) ---
with st.sidebar:
    st.title("✨ Gemini Pro")
    if st.button("➕ Nuevo chat", use_container_width=True):
        new_id = f"Chat {len(st.session_state.all_chats) + 1}"
        st.session_state.all_chats[new_id] = []
        st.session_state.current_chat_id = new_id
        st.rerun()
    
    st.divider()
    st.subheader("Recientes")
    for chat_id in reversed(list(st.session_state.all_chats.keys())):
        if st.button(chat_id, key=chat_id):
            st.session_state.current_chat_id = chat_id
            st.rerun()

# --- FUNCIONES DE DOCUMENTOS ---
def crear_pdf(texto):
    pdf = FPDF()
    pdf.add_page(); pdf.set_font("Arial", size=12)
    pdf.multi_cell(0, 10, txt=texto.encode('latin-1', 'replace').decode('latin-1'))
    return pdf.output(dest='S').encode('latin-1')

def crear_word(texto):
    doc = Document(); doc.add_paragraph(texto)
    bio = io.BytesIO(); doc.save(bio); return bio.getvalue()

# --- PANTALLA PRINCIPAL DE CHAT ---
st.title(st.session_state.current_chat_id)

# Mostrar mensajes del chat actual
current_messages = st.session_state.all_chats[st.session_state.current_chat_id]
for msg in current_messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if "chart" in msg: st.plotly_chart(msg["chart"])
        if "file" in msg: st.download_button(**msg["file"])

# --- BARRA DE ENTRADA CON CLIP ---
with st.container():
    # Esta fila simula la barra de entrada de Gemini
    c1, c2 = st.columns([0.08, 0.92])
    with c1:
        archivo = st.file_uploader("📎", type=["pdf", "png", "jpg", "csv", "xlsx", "txt"], label_visibility="collapsed")
    with c2:
        prompt = st.chat_input("Escribe tu mensaje...")

if prompt:
    contexto_archivo = ""
    img_b64 = None
    
    if archivo:
        if "image" in archivo.type:
            img_b64 = f"data:{archivo.type};base64,{base64.b64encode(archivo.read()).decode()}"
        elif "pdf" in archivo.type:
            reader = PyPDF2.PdfReader(archivo)
            contexto_archivo = "Contenido PDF: " + " ".join([p.extract_text() for p in reader.pages])

    # Guardar mensaje del usuario
    current_messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Respuesta de la IA
    with st.chat_message("assistant"):
        modelo = "llama-3.2-11b-vision-preview" if img_b64 else "llama-3.3-70b-versatile"
        sys_prompt = f"Eres Gemini, una IA avanzada de Google. Hoy es {datetime.now()}. {contexto_archivo}. Si piden gráficos usa [DATA: {{\"item\": valor}}]"
        
        msgs_api = [{"role": "system", "content": sys_prompt}]
        if img_b64:
            msgs_api.append({"role": "user", "content": [{"type": "text", "text": prompt}, {"type": "image_url", "image_url": {"url": img_b64}}]})
        else:
            for m in current_messages[-5:]: msgs_api.append({"role": m["role"], "content": m["content"]})

        placeholder = st.empty(); full_res = ""
        completion = client.chat.completions.create(model=modelo, messages=msgs_api, stream=True)
        
        for chunk in completion:
            if chunk.choices[0].delta.content:
                full_res += chunk.choices[0].delta.content
                placeholder.markdown(full_res + "▌")
        placeholder.markdown(full_res)

        # Empaquetar respuesta
        new_msg = {"role": "assistant", "content": full_res}

        # Gráficos dinámicos
        if "[DATA:" in full_res:
            try:
                import json
                data_json = json.loads(full_res.split("[DATA:")[1].split("]")[0])
                fig = px.pie(names=list(data_json.keys()), values=list(data_json.values()), title="Análisis de Datos")
                st.plotly_chart(fig); new_msg["chart"] = fig
            except: pass

        # Generación de archivos por texto
        p_low = prompt.lower()
        if "pdf" in p_low:
            new_msg["file"] = {"label": "📥 Bajar PDF", "data": crear_pdf(full_res), "file_name": "gemini_doc.pdf"}
        elif "word" in p_low:
            new_msg["file"] = {"label": "📥 Bajar Word", "data": crear_word(full_res), "file_name": "gemini_doc.docx"}
            
        if "file" in new_msg: st.download_button(**new_msg["file"])
        
        current_messages.append(new_msg)
