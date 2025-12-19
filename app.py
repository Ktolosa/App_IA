import streamlit as st
from groq import Groq
import base64
import PyPDF2

# --- 1. CONFIGURACIÓN Y ESTILO ---
st.set_page_config(page_title="Gemini Ultra", page_icon="✨", layout="wide")

st.markdown("""
    <style>
    header, footer {visibility: hidden;}
    .main .block-container { max-width: 850px; padding-bottom: 200px; }
    .stChatFloatingInputContainer { bottom: 30px !important; background-color: transparent !important; }
    
    [data-testid="stFileUploader"] { position: absolute; left: 15px; top: 8px; width: 42px; z-index: 1000; }
    [data-testid="stFileUploader"] section { padding: 0 !important; min-height: 0 !important; border: none !important; }
    [data-testid="stFileUploader"] label, [data-testid="stFileUploader"] small, 
    [data-testid="stFileUploader"] div, [data-testid="stFileUploaderDropzoneInstructions"] { display: none !important; }
    [data-testid="stFileUploader"] button {
        background-color: #f0f4f9 !important; color: transparent !important; border: none !important;
        width: 42px !important; height: 42px !important; border-radius: 50% !important;
    }
    [data-testid="stFileUploader"] button::after {
        content: '📎'; color: #444746; font-size: 20px; position: absolute; 
        top: 50%; left: 50%; transform: translate(-50%, -50%); visibility: visible;
    }
    .stChatInput textarea { border-radius: 28px !important; padding-left: 55px !important; background-color: #f0f4f9 !important; border: none !important; }
    .file-pill { background-color: #e8f0fe; color: #1a73e8; padding: 4px 12px; border-radius: 12px; font-size: 0.8rem; border: 1px solid #c2e7ff; display: inline-flex; align-items: center; gap: 5px; margin-bottom: 5px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. INICIALIZACIÓN ---
if "chats" not in st.session_state:
    st.session_state.chats = {"Chat Inicial": {"history": []}}
if "current_chat" not in st.session_state:
    st.session_state.current_chat = "Chat Inicial"

client = Groq(api_key=st.secrets["GROQ_API_KEY"])

# --- 3. FUNCIONES DE PROCESAMIENTO ---
def get_model(vision=False):
    try:
        available = [m.id for m in client.models.list().data]
        if vision:
            for m in ["llama-3.2-11b-vision-preview", "llama-3.2-90b-vision-preview"]:
                if m in available: return m
        return "llama-3.3-70b-versatile"
    except: return "llama-3.3-70b-versatile"

def process_upload(files):
    text_data, imgs = "", []
    for f in files:
        if "image" in f.type:
            imgs.append(f"data:{f.type};base64,{base64.b64encode(f.getvalue()).decode()}")
        elif "pdf" in f.type:
            pdf = PyPDF2.PdfReader(f)
            text_data += f"\n[Doc: {f.name}]\n" + " ".join([p.extract_text() for p in pdf.pages])
        else:
            text_data += f"\n[Doc: {f.name}]\n" + f.getvalue().decode()
    return text_data, imgs

# --- 4. GESTIÓN DE CHATS ---
curr = st.session_state.current_chat
if curr not in st.session_state.chats:
    curr = list(st.session_state.chats.keys())[0]

with st.sidebar:
    st.title("✨ Gemini")
    if st.button("➕ Nuevo Chat", use_container_width=True):
        new_name = f"Chat {len(st.session_state.chats) + 1}"
        st.session_state.chats[new_name] = {"history": []}
        st.session_state.current_chat = new_name
        st.rerun()
    st.divider()
    for chat_id in list(st.session_state.chats.keys()):
        col_c, col_d = st.columns([0.8, 0.2])
        if col_c.button(chat_id, key=f"s_{chat_id}", use_container_width=True):
            st.session_state.current_chat = chat_id
            st.rerun()
        if col_d.button("🗑️", key=f"d_{chat_id}"):
            if len(st.session_state.chats) > 1:
                del st.session_state.chats[chat_id]
                st.session_state.current_chat = list(st.session_state.chats.keys())[0]
                st.rerun()

# --- 5. INTERFAZ DE CHAT ---
new_title = st.text_input("Title", value=curr, label_visibility="collapsed")
if new_title != curr and new_title.strip() != "":
    st.session_state.chats[new_title] = st.session_state.chats.pop(curr)
    st.session_state.current_chat = new_title
    st.rerun()

for m in st.session_state.chats[curr]["history"]:
    with st.chat_message(m["role"]):
        # Si el contenido es una lista (formato imagen), solo mostrar el texto para no romper la UI
        if isinstance(m["content"], list):
            st.markdown(m["content"][0]["text"])
        else:
            st.markdown(m["content"])

# --- 6. ENTRADA ---
with st.container():
    u_files = st.file_uploader("Adjuntar", accept_multiple_files=True, key=f"u_{curr}", label_visibility="collapsed")
    if u_files:
        st.markdown('<div style="margin-left:55px;">', unsafe_allow_html=True)
        for f in u_files:
            st.markdown(f'<div class="file-pill">📄 {f.name}</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    prompt = st.chat_input("Escribe a Gemini...")

# --- 7. LÓGICA DE RESPUESTA (CON LIMPIEZA DE HISTORIAL) ---
if prompt:
    # 1. Guardar mensaje del usuario (como texto simple para el historial futuro)
    st.session_state.chats[curr]["history"].append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    txt_ctx, img_ctx = process_upload(u_files)
    sel_model = get_model(vision=len(img_ctx) > 0)

    with st.chat_message("assistant"):
        ph = st.empty()
        full_res = ""
        
        # 2. CONSTRUIR PAYLOAD LIMPIO PARA GROQ
        msgs_for_api = [{"role": "system", "content": "Eres Gemini Ultra. Responde con precisión."}]
        
        # Limpiar historial previo: Convertir cualquier lista en string
        for h in st.session_state.chats[curr]["history"][:-1]: # Todos menos el último
            content = h["content"]
            if isinstance(content, list): content = content[0]["text"]
            msgs_for_api.append({"role": h["role"], "content": str(content)})
        
        # 3. Preparar mensaje ACTUAL (el que puede llevar imágenes)
        current_user_content = f"[ARCHIVOS ADJUNTOS]\n{txt_ctx}\n\n[PREGUNTA]: {prompt}" if txt_ctx else prompt
        
        if img_ctx:
            content_structure = [{"type": "text", "text": current_user_content}]
            for img in img_ctx:
                content_structure.append({"type": "image_url", "image_url": {"url": img}})
            msgs_for_api.append({"role": "user", "content": content_structure})
        else:
            msgs_for_api.append({"role": "user", "content": current_user_content})

        try:
            stream = client.chat.completions.create(model=sel_model, messages=msgs_for_api, stream=True)
            for chunk in stream:
                if chunk.choices[0].delta.content:
                    full_res += chunk.choices[0].delta.content
                    ph.markdown(full_res + "▌")
            ph.markdown(full_res)
            st.session_state.chats[curr]["history"].append({"role": "assistant", "content": full_res})
            st.rerun()
        except Exception as e:
            st.error(f"Error: {e}")
