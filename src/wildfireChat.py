
import streamlit as st
import pandas as pd
import pickle

st.title("Wildfire GPT")

import clipboard
from src.tools import *
from config import model, client
from src.utils import populate_tools, run_conversation, load_config

with open("prompt/prompt.md", "r") as f:
    template = f.read()


config = load_config("src/tools/config.yml")
tools = populate_tools(config)
available_functions = {
    "LiteratureSearch": literature_search,
    "FWI": FWI_retrieval,
    "history": find_closest_fire_histories_within_50_miles,
    "incident": generate_recent_wildfire_incident_summary_report,
    "checklist": checklist_of_questions,
}

def on_copy_click(text):
    st.session_state.copied.append(text)
    clipboard.copy(text)

if "copied" not in st.session_state: 
    st.session_state.copied = []

init_message = {"role": "assistant", "content": "Hello! I'm here to assist you with any questions or concerns you may have regarding wildfires. Could you please share with me why you are interested in learning about wildfires? Additionally, is there a specific project or task where wildfires could potentially have an impact on your plans?"}

if "messages" not in st.session_state:
    st.session_state.messages = [init_message]
    st.session_state.openAI_messages = []
    st.session_state.summary_message = None
    st.session_state.index = 3
    st.session_state.visualize = None

def run_conversation_(messages):
    response = run_conversation(messages, tools, available_functions, config)
    return response

index = 0
for message in st.session_state.messages:
    # if message is a list, it means it contains a visualization
    
    if type(message) == list:
        with st.chat_message(message[0]["role"]):
            st.markdown(message[0]["content"])
            fig = message[1]["fig"]
            st.plotly_chart(fig, use_container_width=True)
            if message[0]["role"] == "assistant":
                st.button("📋", on_click=on_copy_click, args=(message[0]["content"],), key=index)
                index += 1
    else:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            if message["role"] == "assistant":
                st.button("📋", on_click=on_copy_click, args=(message["content"],), key=index)
                index += 1

if prompt := st.chat_input("Ask me anything?"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.session_state.openAI_messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        full_response = ""
        messages = run_conversation_(
            messages=st.session_state.openAI_messages
        )
        if type(messages) == str:
            full_response = messages
        else:
            if len(messages) > 3:
                try:
                    summary_message = client.chat.completions.create(
                        model=model,
                        messages=messages[:-3] + [{"role": "system", "content": "summarize the previous conversation"}],
                    ).choices[0].message
                    print("\n\n\n")
                    print(summary_message)
                    print("\n\n\n")
                    messages = [summary_message, init_message] + messages[-3:]
                    st.session_state.index = 3
                except:
                    summary_message = client.chat.completions.create(
                        model=model,
                        messages=messages[:-2] + [{"role": "system", "content": "summarize the previous conversation"}],
                    ).choices[0].message
                    messages = [summary_message, init_message] + messages[-2:]
                    st.session_state.index = 2
                st.session_state.summary_message = summary_message
                st.session_state.openAI_messages = messages
            
            st.session_state.visualize = pickle.load(open("temp", "rb"))

            if st.session_state.visualize:
                fig = st.session_state.visualize
                st.plotly_chart(fig, use_container_width=True)
                # clear the temp file
                pickle.dump(None, open("temp", "wb"))
            
            for response in client.chat.completions.create(
                model=model,
                messages=messages,
                stream=True,
            ):
                full_response += (response.choices[0].delta.content or "")
                message_placeholder.markdown(full_response + "▌")
        
        message_placeholder.markdown(full_response)

    if st.session_state.visualize:
        st.session_state.messages.append([{"role": "assistant", "content": full_response}, {"fig": st.session_state.visualize}])
        st.session_state.visualize = None
    else:
        st.session_state.messages.append({"role": "assistant", "content": full_response})
    st.session_state.openAI_messages.append({"role": "assistant", "content": full_response})

    st.rerun()
