import streamlit as st
from groq import Groq
import base64
import PyPDF2
from datetime import datetime

# --- 1. CONFIGURACIÓN Y ESTILO (DISEÑO GEMINI TOTAL) ---
st.set_page_config(page_title="Gemini Ultra Autómata", page_icon="✨", layout="wide")

st.markdown("""
    <style>
    header, footer {visibility: hidden;}
    .main .block-container { max-width: 850px; padding-bottom: 180px; }

    /* BARRA INFERIOR FIJA */
    .stChatFloatingInputContainer { bottom: 30px !important; background-color: white !important; }

    /* ALINEACIÓN EN LÍNEA: CLIP + BARRA */
    [data-testid="stForm"] {
        display: flex !important;
        flex-direction: row !important;
        align-items: center !important;
        gap: 10px !important;
        border: none !important;
    }

    /* LIMPIEZA DEL CARGADOR (SOLO ICONO) */
    [data-testid="stFileUploader"] { width: 45px !important; margin-bottom: 0px !important; }
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
    .stChatInput textarea { border-radius: 24px !important; background-color: #f0f2f6 !important; padding-top: 12px !important; }

    .pill-container { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 10px; padding-left: 55px; }
    .file-pill { background-color: #e8f0fe; color: #1a73e8; padding: 4px 12px; border-radius: 15px; font-size: 0.85rem; border: 1px solid #c2e7ff; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. INICIALIZACIÓN ---
if "chats" not in st.session_state:
    st.session_state.chats = {"Chat 1": []}
if "current_chat" not in st.session_state:
    st.session_state.current_chat = "Chat 1"

client = Groq(api_key=st.secrets["GROQ_API_KEY"])

# --- 3. LÓGICA DE AUTO-SELECCIÓN DE MODELOS REAL-TIME ---
def obtener_modelos_dinamicos(es_vision=False):
    """Consulta los modelos activos en Groq y selecciona el mejor disponible."""
    try:
        modelos_disponibles = [m.id for m in client.models.list().data]
        
        if es_vision:
            # Buscamos modelos que soporten visión (actualmente llama-3.2-11b-vision-preview o similares)
            vision_models = [m for m in modelos_disponibles if "vision" in m.lower()]
            if vision_models:
                # Priorizamos los más nuevos/potentes si hay varios
                return sorted(vision_models, reverse=True)[0]
        else:
            # Priorizamos modelos versátiles y potentes para texto (70b o 3.3)
            text_models = [m for m in modelos_disponibles if "70b" in m.lower() or "versatile" in m.lower()]
            if text_models:
                return text_models[0]
            
        # Si no hay match específico, devolvemos el primero de la lista que sea de chat
        return modelos_disponibles[0]
    except Exception as e:
        # Fallback de emergencia si la lista falla
        return "llama-3.3-70b-versatile"

# --- 4. PROCESAMIENTO DE ARCHIVOS ---
def procesar_archivos(archivos_subidos):
    text_ctx, img_list = "", []
    for f in archivos_subidos:
        if "image" in f.type:
            b64_data = base64.b64encode(f.read()).decode()
            img_list.append(f"data:{f.type};base64,{b64_data}")
        elif "pdf" in f.type:
            reader = PyPDF2.PdfReader(f)
            text_ctx += f"\n[Doc: {f.name}]\n" + " ".join([p.extract_text() for p in reader.pages])
        else:
            text_ctx += f"\n[Doc: {f.name}]\n" + f.read().decode()
    return text_ctx, img_list

# --- 5. SIDEBAR (HISTORIAL) ---
with st.sidebar:
    st.title("✨ Gemini")
    if st.button("➕ Nuevo chat", use_container_width=True):
        nuevo = f"Chat {len(st.session_state.chats) + 1}"
        st.session_state.chats[nuevo] = []
        st.session_state.current_chat = nuevo
        st.rerun()
    st.divider()
    for c_id in reversed(list(st.session_state.chats.keys())):
        if st.button(c_id, key=f"nav_{c_id}", use_container_width=True):
            st.session_state.current_chat = c_id
            st.rerun()

# --- 6. CHAT Y ENTRADA ---
st.subheader(st.session_state.current_chat)
history = st.session_state.chats[st.session_state.current_chat]

for msg in history:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

with st.container():
    archivos = st.file_uploader("", type=["pdf", "png", "jpg", "txt", "csv"], 
                                 accept_multiple_files=True, label_visibility="collapsed")
    if archivos:
        st.markdown('<div class="pill-container">', unsafe_allow_html=True)
        for f in archivos:
            st.markdown(f'<div class="file-pill">📄 {f.name}</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    prompt = st.chat_input("Escribe tu consulta aquí...")

# --- 7. LÓGICA DE RESPUESTA AUTOMATIZADA ---
if prompt:
    history.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    contexto_texto, lista_imagenes = procesar_archivos(archivos)
    
    with st.chat_message("assistant"):
        placeholder = st.empty()
        full_res = ""
        
        # BUSCAR MODELO ACTUALIZADO EN TIEMPO REAL
        modelo_activo = obtener_modelos_dinamicos(es_vision=len(lista_imagenes) > 0)
        
        if len(lista_imagenes) > 0:
            content_payload = [{"type": "text", "text": f"{contexto_texto}\n\n{prompt}"}]
            for img in lista_imagenes:
                content_payload.append({"type": "image_url", "image_url": {"url": img}})
            msgs = [{"role": "user", "content": content_payload}]
        else:
            # Enviamos el historial completo para tener memoria
            msgs = [{"role": "system", "content": "Eres un asistente inteligente. Responde de forma clara."}]
            for h in history[-6:]: # Enviamos últimos 6 mensajes para contexto
                msgs.append({"role": h["role"], "content": h["content"]})
            # Actualizamos el último mensaje con el contexto de los archivos si los hay
            if contexto_texto:
                msgs[-1]["content"] = f"{contexto_texto}\n\n{prompt}"

        try:
            stream = client.chat.completions.create(model=modelo_activo, messages=msgs, stream=True)
            for chunk in stream:
                if chunk.choices[0].delta.content:
                    full_res += chunk.choices[0].delta.content
                    placeholder.markdown(full_res + "▌")
            placeholder.markdown(full_res)
            history.append({"role": "assistant", "content": full_res})
            st.rerun()
        except Exception as e:
            st.error(f"Error de conexión con Groq: {e}. Intenta recargar la página.")
