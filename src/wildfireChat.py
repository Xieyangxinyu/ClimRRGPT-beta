
import streamlit as st
import pickle
from src.memory import Profile, profile_wizard

st.title("Wildfire GPT")

import clipboard
from src.tools import *
from config import model, client
from src.utils import populate_tools, run_conversation, load_config

with open("prompt/prompt.md", "r") as f:
    prompt = f.read()


config = load_config("src/tools/config.yml")
tools = populate_tools(config)
available_functions = {
    "LiteratureSearch": literature_search,
    "FWI": FWI_retrieval,
    "history": find_closest_fire_histories_within_10_miles,
    "incident": generate_recent_wildfire_incident_summary_report,
    "checklist": checklist_of_questions,
}

def on_copy_click(text):
    st.session_state.copied.append(text)
    clipboard.copy(text)

if "copied" not in st.session_state: 
    st.session_state.copied = []

if "user" not in st.session_state:
    st.session_state.user = Profile()
    st.session_state.user.messages = [None, None]

init_message = {"role": "assistant", "content": "Hello! I'm here to assist you with any questions or concerns you may have regarding wildfires. Could you please share with me why you are interested in learning about wildfires? Additionally, is there a specific project or task where wildfires could potentially have an impact on your plans?"}
prompt_message =  {"role": "system", "content": f"{prompt}"}
summary_prompt = "Summarize the previous conversation in detail. 1. highlight importance information about wildfire that will help you mkae recommendations. 2. Detail all the answers that the user provided to the clarifying questions that you asked. For example, if there is a location, make sure you include the latitude and longitude of the location. 3. explain where you are in terms of your plan to help the user. What is the next step? "

if "messages" not in st.session_state:
    st.session_state.messages = [init_message]
    st.session_state.openAI_messages = [prompt_message, init_message]
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
            visualize = message[1]["fig"]
            for fig in visualize:
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

if user_prompt := st.chat_input("Ask me anything?"):
    st.session_state.messages.append({"role": "user", "content": user_prompt})
    st.session_state.openAI_messages.append({"role": "user", "content": user_prompt})
    
    with st.chat_message("user"):
        st.markdown(user_prompt)

    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        full_response = ""
        if st.session_state.user.profile_complete:
            response_messages = run_conversation_(
                messages=st.session_state.openAI_messages
            )
        else:
            response_messages = profile_wizard(st.session_state.user, st.session_state.openAI_messages)
        if type(response_messages) == str:
            full_response = response_messages
        else:
            st.session_state.openAI_messages = response_messages
        
        if st.session_state.user.profile_complete and len(st.session_state.openAI_messages) > 7:
            messages = st.session_state.openAI_messages
            memory = {"role": "assistant", "content": f"Here is the user's profile: {st.session_state.user.summary}.\nHere is my plan to assist the user: {st.session_state.user.plan}."}
            try:
                summary_message = client.chat.completions.create(
                    model=model,
                    messages=messages[:-4] + [{"role": "system", "content": summary_prompt}],
                ).choices[0].message
                messages = [prompt_message, memory, summary_message] + messages[-4:]
            except:
                summary_message = client.chat.completions.create(
                    model=model,
                    messages=messages[:-5] + [{"role": "system", "content": summary_prompt}],
                ).choices[0].message
                messages = [prompt_message, summary_message] + messages[-5:]
            
            print("\n\n\n")
            for message in messages:
                try:
                    print(message["role"])
                    print(message["content"])
                except:
                    print(message.role)
                    print(message.content)
            print("\n\n\n")
        
        if type(response_messages) != str:
            st.session_state.visualize = pickle.load(open("temp", "rb"))

            if st.session_state.visualize:
                for fig in st.session_state.visualize:
                    st.plotly_chart(fig, use_container_width=True)
                # clear the temp file
                pickle.dump(None, open("temp", "wb"))
            
            for response in client.chat.completions.create(
                model=model,
                messages=response_messages,
                stream=True,
            ):
                full_response += (response.choices[0].delta.content or "")
                message_placeholder.markdown(full_response + "▌")
            
            # if there is tool message in messages, remove it and the message before it
            for i, message in enumerate(response_messages):
                if type(message) != dict and message.role == "tool":
                    response_messages = response_messages[:i-1] + response_messages[i+1:]
                    break
            
            st.session_state.openAI_messages = response_messages
        message_placeholder.markdown(full_response)

    if st.session_state.visualize:
        st.session_state.messages.append([{"role": "assistant", "content": full_response}, {"fig": st.session_state.visualize}])
        st.session_state.visualize = None
    else:
        st.session_state.messages.append({"role": "assistant", "content": full_response})
    
    st.session_state.openAI_messages.append({"role": "assistant", "content": full_response})

    st.rerun()
