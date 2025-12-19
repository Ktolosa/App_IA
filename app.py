import streamlit as st
from groq import Groq
import base64
import PyPDF2

# --- 1. CONFIGURACIÓN Y ESTILO ---
st.set_page_config(page_title="Gemini Ultra Pro", page_icon="✨", layout="wide")

st.markdown("""
    <style>
    header, footer {visibility: hidden;}
    .main .block-container { max-width: 850px; padding-bottom: 180px; }
    .stChatFloatingInputContainer { bottom: 30px !important; background-color: white !important; }
    
    /* ALINEACIÓN CLIP + INPUT */
    [data-testid="stForm"] { display: flex !important; align-items: center !important; gap: 10px !important; border: none !important; }
    [data-testid="stFileUploader"] { width: 45px !important; }
    [data-testid="stFileUploader"] section { padding: 0 !important; min-height: 0 !important; border: none !important; }
    [data-testid="stFileUploader"] label, [data-testid="stFileUploader"] small, 
    [data-testid="stFileUploader"] div, [data-testid="stFileUploaderDropzoneInstructions"] { display: none !important; }
    [data-testid="stFileUploader"] button {
        background-color: #f0f2f6 !important; color: transparent !important; border: none !important;
        width: 44px !important; height: 44px !important; border-radius: 50% !important;
    }
    [data-testid="stFileUploader"] button::after {
        content: '📎'; color: #444746; font-size: 22px; position: absolute; top: 50%; left: 50%;
        transform: translate(-50%, -50%); visibility: visible;
    }
    
    .stChatInput { flex-grow: 1 !important; }
    .pill-container { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 10px; padding-left: 55px; }
    .file-pill { background-color: #e8f0fe; color: #1a73e8; padding: 4px 12px; border-radius: 15px; font-size: 0.85rem; border: 1px solid #c2e7ff; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. INICIALIZACIÓN DE SESIÓN ---
if "chats" not in st.session_state:
    st.session_state.chats = {
        "Chat Inicial": {"history": [], "files": []}
    }
if "current_chat" not in st.session_state:
    st.session_state.current_chat = "Chat Inicial"

client = Groq(api_key=st.secrets["GROQ_API_KEY"])

# --- 3. FUNCIONES CORE ---
def get_best_model(is_vision=False):
    try:
        models = [m.id for m in client.models.list().data]
        if is_vision:
            vision_opts = [m for m in models if "vision" in m.lower()]
            return sorted(vision_opts, reverse=True)[0] if vision_opts else "llama-3.2-11b-vision-preview"
        text_opts = [m for m in models if "70b" in m.lower() or "versatile" in m.lower()]
        return text_opts[0] if text_opts else models[0]
    except:
        return "llama-3.3-70b-versatile"

def process_files(files):
    text_ctx, imgs = "", []
    for f in files:
        if "image" in f.type:
            imgs.append(f"data:{f.type};base64,{base64.b64encode(f.getvalue()).decode()}")
        elif "pdf" in f.type:
            pdf = PyPDF2.PdfReader(f)
            text_ctx += f"\n[Doc: {f.name}]\n" + " ".join([p.extract_text() for p in pdf.pages])
        else:
            text_ctx += f"\n[Doc: {f.name}]\n" + f.getvalue().decode()
    return text_ctx, imgs

# --- 4. SIDEBAR (GESTIÓN DE CHATS) ---
with st.sidebar:
    st.title("✨ Gemini Ultra")
    if st.button("➕ Nuevo Chat", use_container_width=True):
        new_name = f"Chat {len(st.session_state.chats) + 1}"
        st.session_state.chats[new_name] = {"history": [], "files": []}
        st.session_state.current_chat = new_name
        st.rerun()
    
    st.divider()
    for chat_id in list(st.session_state.chats.keys()):
        col_name, col_del = st.columns([0.8, 0.2])
        if col_name.button(chat_id, key=f"sel_{chat_id}", use_container_width=True):
            st.session_state.current_chat = chat_id
            st.rerun()
        if col_del.button("🗑️", key=f"del_{chat_id}"):
            if len(st.session_state.chats) > 1:
                del st.session_state.chats[chat_id]
                st.session_state.current_chat = list(st.session_state.chats.keys())[0]
                st.rerun()

# --- 5. INTERFAZ PRINCIPAL ---
current = st.session_state.current_chat
chat_data = st.session_state.chats[current]

# Editar nombre del chat
new_chat_name = st.text_input("Nombre del chat", value=current, label_visibility="collapsed")
if new_chat_name != current:
    st.session_state.chats[new_chat_name] = st.session_state.chats.pop(current)
    st.session_state.current_chat = new_chat_name
    st.rerun()

# Historial
for m in chat_data["history"]:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

# --- 6. ÁREA DE ENTRADA Y ARCHIVOS ---
with st.container():
    # Solo cargamos archivos si no han sido procesados o para añadir nuevos
    uploaded = st.file_uploader("Adjuntar", accept_multiple_files=True, key=f"up_{current}", label_visibility="collapsed")
    
    if uploaded:
        chat_data["files"] = uploaded # Se guardan solo en este chat
        st.markdown('<div class="pill-container">', unsafe_allow_html=True)
        for f in uploaded:
            st.markdown(f'<div class="file-pill">📄 {f.name}</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
        if st.button("Limpiar archivos", key=f"clr_{current}"):
            chat_data["files"] = []
            st.rerun()

    prompt = st.chat_input("Escribe a Gemini...")

# --- 7. PROCESAMIENTO ---
if prompt:
    chat_data["history"].append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    txt_ctx, img_ctx = process_files(chat_data["files"])
    model = get_best_model(is_vision=len(img_ctx) > 0)

    with st.chat_message("assistant"):
        ph = st.empty()
        full_res = ""
        
        msgs = [{"role": "system", "content": "Asistente experto. Analiza el contexto de archivos si se provee."}]
        # Memoria de chat
        for h in chat_data["history"][-6:]:
            msgs.append(h)
        
        # Inyectar contexto de archivos en el último mensaje
        if txt_ctx:
            msgs[-1]["content"] = f"CONTEXTO ARCHIVOS:\n{txt_ctx}\n\nPREGUNTA:\n{prompt}"
        
        if img_ctx:
            content = [{"type": "text", "text": msgs[-1]["content"]}]
            for img in img_ctx:
                content.append({"type": "image_url", "image_url": {"url": img}})
            msgs[-1]["content"] = content

        try:
            stream = client.chat.completions.create(model=model, messages=msgs, stream=True)
            for chunk in stream:
                if chunk.choices[0].delta.content:
                    full_res += chunk.choices[0].delta.content
                    ph.markdown(full_res + "▌")
            ph.markdown(full_res)
            chat_data["history"].append({"role": "assistant", "content": full_res})
            st.rerun()
        except Exception as e:
            st.error(f"Error: {e}")
