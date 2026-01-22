import streamlit as st
import requests
import uuid

# --- CONFIGURAÇÃO ---
ST_PAGE_TITLE = "🤖 AI Hello World Agent"
API_URL = "http://localhost:8000/chat"  # O endereço do teu FastAPI

st.set_page_config(page_title=ST_PAGE_TITLE, page_icon="🤖")

# --- GESTÃO DE ESTADO (SESSION STATE) ---
# O Streamlit "reinicia" o script a cada clique. 
# Precisamos do session_state para lembrar o histórico e o ID da sessão.

if "messages" not in st.session_state:
    st.session_state.messages = []

# Gera um ID único para este utilizador se ainda não existir
if "thread_id" not in st.session_state:
    st.session_state.thread_id = str(uuid.uuid4())

# --- SIDEBAR (Barra Lateral) ---
with st.sidebar:
    st.header("Debug Info")
    st.text(f"Session ID:\n{st.session_state.thread_id}")
    if st.button("Limpar Conversa"):
        st.session_state.messages = []
        # Gera novo ID para começar "do zero" na memória do Agente
        st.session_state.thread_id = str(uuid.uuid4()) 
        st.rerun()

# --- INTERFACE PRINCIPAL ---
st.title("Hello World!")
st.caption("Powered by FastAPI, LangGraph & Gemini")

# 1. Mostrar histórico de mensagens
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# 2. Caixa de Entrada do Utilizador
if prompt := st.chat_input("Ex: Cria um servidor na Europa..."):
    
    # A. Mostrar a mensagem do utilizador imediatamente
    with st.chat_message("user"):
        st.markdown(prompt)
    
    # Guardar no histórico local
    st.session_state.messages.append({"role": "user", "content": prompt})

    # B. Chamar o Backend (FastAPI)
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        message_placeholder.markdown("⏳ A pensar...")

        try:
            # Prepara o payload igual ao que definimos no Pydantic do backend
            payload = {
                "message": prompt,
                "thread_id": st.session_state.thread_id
            }
            
            # Request POST
            response = requests.post(API_URL, json=payload)
            response.raise_for_status() # Lança erro se for 4xx ou 5xx

            data = response.json()
            try:
                agent_response = data["response"][0]["text"]
            except:
                agent_response = data["response"]
            
            # Atualiza o placeholder com a resposta real
            message_placeholder.markdown(agent_response)
            
            # Guardar a resposta no histórico local
            st.session_state.messages.append({"role": "assistant", "content": agent_response})

        except requests.exceptions.ConnectionError:
            message_placeholder.error("❌ Erro: Não consigo conectar ao Backend. O FastAPI está a correr?")
        except Exception as e:
            message_placeholder.error(f"❌ Ocorreu um erro: {e}")