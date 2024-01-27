
import streamlit as st
from init import *

st.title("Wildfire GPT")

def on_copy_click(text):
    st.session_state.copied.append(text)
    clipboard.copy(text)

if "copied" not in st.session_state: 
    st.session_state.copied = []

if "user" not in st.session_state:
    st.session_state.user = Profile()
    st.session_state.user.messages = [None, None]

if "messages" not in st.session_state:
    st.session_state.messages = [init_message]
    st.session_state.openAI_messages = [prompt_message, init_message]
    st.session_state.visualize = None
    st.session_state.save_state = 0

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
        response_messages = get_response(
            user = st.session_state.user,
            messages=st.session_state.openAI_messages
        )
        if type(response_messages) == str:
            full_response = response_messages
        else:
            st.session_state.openAI_messages = response_messages
        
        if st.session_state.user.profile_complete and len(st.session_state.openAI_messages) > 7:
            messages = st.session_state.openAI_messages
            memory = get_memory_prompt(st.session_state.user)
            try:
                summary_message = client.chat.completions.create(
                    model=model,
                    messages=messages[:-4] + [summary_prompt],
                ).choices[0].message
                messages = [prompt_message, memory, summary_message] + messages[-4:]
            except:
                summary_message = client.chat.completions.create(
                    model=model,
                    messages=messages[:-5] + [summary_prompt],
                ).choices[0].message
                messages = [prompt_message, memory, summary_message] + messages[-5:]
            
            save_content = ""
            for message in messages:
                try:
                    save_content += f"{message['role']}: {message['content']}\n\n\n"
                except:
                    save_content += f"{message.role}: {message.content}\n\n\n"
            # save messages
            with open(chat_history_path + f"memory_{st.session_state.save_state}", "w") as f:
                f.write(save_content)
            st.session_state.save_state += 1
        
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

    # save the chat history
    with open(chat_history_path + "chat_history.txt", "a") as f:
        f.write(f"User: {user_prompt}\nAssistant: {full_response}\n\n")

    st.rerun()
