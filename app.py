import streamlit as st
from groq import Groq

# Configuración de la página
st.set_page_config(page_title="Mi IA con Groq", page_icon="🤖")
st.title("🤖 Mi Asistente Inteligente")

# Configurar la API Key (la pediremos en la interfaz por seguridad)
api_key = st.sidebar.text_input("Ingresa tu Groq API Key", type="password")

if api_key:
    client = Groq(api_key=api_key)

    # Inicializar el historial de chat
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Mostrar mensajes previos
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Entrada del usuario
    if prompt := st.chat_input("¿En qué puedo ayudarte hoy?"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Respuesta de la IA
        with st.chat_message("assistant"):
            chat_completion = client.chat.completions.create(
                messages=[{"role": m["role"], "content": m["content"]} for m in st.session_state.messages],
                model="llama-3.3-70b-versatile", # El modelo más potente disponible
            )
            response = chat_completion.choices[0].message.content
            st.markdown(response)
        
        st.session_state.messages.append({"role": "assistant", "content": response})
else:
    st.warning("Por favor, introduce tu API Key en la barra lateral para comenzar.")
