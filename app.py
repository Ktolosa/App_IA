import streamlit as st
from groq import Groq
from datetime import datetime

# 1. Configuración de la App
st.set_page_config(page_title="IA Avanzada", page_icon="🧠", layout="centered")

# Estilo personalizado para que se vea más profesional
st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    .stChatMessage { border-radius: 15px; }
    </style>
    """, unsafe_allow_html=True)

st.title("🧠 Inteligencia Artificial Pro")
st.caption("Impulsada por Groq LPU y Llama 3.3 (70B)")

# 2. Configuración de la API Key por defecto
# Intentará leerla de los secretos de Streamlit automáticamente
try:
    api_key = st.secrets["GROQ_API_KEY"]
    client = Groq(api_key=api_key)
except Exception:
    st.error("⚠️ Error: Configura tu GROQ_API_KEY en los Secrets de Streamlit.")
    st.stop()

# 3. Gestión de la Memoria (Historial)
if "messages" not in st.session_state:
    st.session_state.messages = []

# Botón para limpiar memoria
if st.sidebar.button("Limpiar Memoria"):
    st.session_state.messages = []
    st.rerun()

# 4. Renderizar chat
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# 5. Lógica de Inteligencia
if prompt := st.chat_input("Escribe tu duda aquí..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        # Instrucciones de "Súper Inteligencia" (System Prompt)
        fecha_actual = datetime.now().strftime("%d/%m/%Y %H:%M")
        
        system_instruction = {
            "role": "system",
            "content": f"""Eres una IA de última generación altamente analítica.
            Fecha y hora actual: {fecha_actual}.
            Instrucciones:
            1. Responde siempre en español de forma elegante y profesional.
            2. Si la consulta es compleja, razona paso a paso antes de dar la respuesta final.
            3. Tienes memoria total de esta conversación actual.
            4. Eres experto en programación, ciencia y cultura general."""
        }

        # Preparamos el paquete de mensajes (Instrucción + Historial)
        full_history = [system_instruction] + [
            {"role": m["role"], "content": m["content"]} 
            for m in st.session_state.messages
        ]

        try:
            # Creamos un contenedor vacío para el efecto de "streaming" (escritura en tiempo real)
            response_placeholder = st.empty()
            full_response = ""

            completion = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=full_history,
                temperature=0.7, # Creatividad equilibrada
                max_tokens=2048,
                stream=True # Activamos el streaming para que sea más rápida
            )

            for chunk in completion:
                content = chunk.choices[0].delta.content
                if content:
                    full_response += content
                    response_placeholder.markdown(full_response + "▌")
            
            response_placeholder.markdown(full_response)
            st.session_state.messages.append({"role": "assistant", "content": full_response})

        except Exception as e:
            st.error(f"Hubo un error: {e}")
