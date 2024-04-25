from src.assistants.assistant_router import AssistantRouter
import streamlit as st

st.title("Wildfire GPT")

if "messages" not in st.session_state:
    st.session_state.messages = []
    st.session_state.thread_id = None
    st.session_state.assistant = AssistantRouter("ChecklistAssistant")
    with st.chat_message("assistant"):
        full_response = st.session_state.assistant.get_assistant_response()
    st.session_state.messages.append({"role": "assistant", "content": full_response})
    st.rerun()


def display_reponse(response):
    if type(response) != str:
        response, figs = response
        for fig in figs:
            st.plotly_chart(fig, use_container_width=True)
    st.markdown(response)


for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        display_reponse(message["content"])

if user_prompt := st.chat_input("Ask me anything?"):
    with st.chat_message("user"):
        display_reponse(user_prompt)
    
    st.session_state.messages.append({"role": "user", "content": user_prompt})

    with st.chat_message("assistant"):
        full_response = st.session_state.assistant.get_assistant_response(user_prompt)
    
    st.session_state.messages.append({"role": "assistant", "content": full_response})
    st.rerun()
