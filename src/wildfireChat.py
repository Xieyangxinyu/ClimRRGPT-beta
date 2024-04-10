
import streamlit as st
from init import *
import json

st.title("Wildfire GPT")

def on_copy_click(text):
    st.session_state.copied.append(text)
    clipboard.copy(text)

def display_message_content(message, index):
    """Displays the message content and a copy button if applicable."""
    st.markdown(message["content"])
    like_key = f"like_{index}"
    dislike_key = f"dislike_{index}"
    feedback_key = f"feedback_{index}"

    if message["role"] == "assistant":
        col1, col2, col3 = st.columns([1, 1, 2])
        # Render like button or indicate it's been pressed
        if st.session_state.get(like_key) or message.get("liked"):
            col1.success("Liked 👍")
            message["liked"] = True
            message["disliked"] = False
        else:
            if col1.button("👍", key=like_key):
                st.session_state[like_key] = True  # Mark as liked
                message["liked"] = True  # Mark as liked
                message["disliked"] = False  # Mark as not disliked

        # Similarly for dislike button
        if st.session_state.get(dislike_key) or message.get("disliked"):
            col2.error("Disliked 👎")
            message["liked"] = False  # Mark as not liked
            message["disliked"] = True
        else:
            if col2.button("👎", key=dislike_key):
                st.session_state[dislike_key] = True
                message["liked"] = False
                message["disliked"] = True
        col3.button("📋", on_click=on_copy_click, args=(message["content"],), key=index)

        if feedback_key not in st.session_state:
            st.session_state[feedback_key] = ""

        feedback = st.text_input("Feedback", key=feedback_key)
        
        if feedback:
            message["feedback"] = feedback

        json.dump(message, file, indent=4)

        return 1  # Return 1 to indicate that the index should be incremented
    return 0  # Return 0 to indicate no change in index

def display_visualizations(visualizations):
    """Displays visualizations if present."""
    for fig in visualizations:
        st.plotly_chart(fig, use_container_width=True)

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
with open("chat_history/interaction.json", "w") as file:
    for message in st.session_state.messages:
        like_key = f"like_{index}"
        dislike_key = f"dislike_{index}"
        if type(message) == list:
            message_content, visualizations = message
            with st.chat_message(message_content["role"]):
                index += display_message_content(message_content[0], index)
                display_visualizations(visualizations["fig"])
        else:
            with st.chat_message(message["role"]):
                index += display_message_content(message, index)
            


if user_prompt := st.chat_input("Ask me anything?"):
    st.session_state.messages.append({"role": "user", "content": user_prompt})
    st.session_state.openAI_messages.append({"role": "user", "content": user_prompt})
    # remove all messages from OpenAI_messages that are not user or assistant
    if st.session_state.user.profile_complete:
        # save all openAI_messages
        
        save_content = ""
        for message in st.session_state.openAI_messages:
            try:
                save_content += f"{message['role']}: {message['content']}\n\n\n"
            except:
                save_content += f"{message.role}: {message.content}\n\n\n"
        # save messages
        with open(chat_history_path + f"memory_profile", "w") as f:
            f.write(save_content)
        st.session_state.openAI_messages = [message for message in st.session_state.openAI_messages if type(message) == dict]
        st.session_state.openAI_messages = [message for message in st.session_state.openAI_messages if message["role"] in ["user", "assistant", "system"]]

    temp = st.session_state.user.profile_complete
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
        if temp != st.session_state.user.profile_complete:
            memory = get_memory_prompt(st.session_state.user)
            st.session_state.openAI_messages = [prompt_message, memory]

        if st.session_state.user.profile_complete and (len(st.session_state.openAI_messages) % 10 == 0):
            messages = st.session_state.openAI_messages
            '''
            memory = get_memory_prompt(st.session_state.user)
            try:
                summary_message = client.chat.completions.create(
                    model=model,
                    messages=messages[2:-7] + [summary_prompt],
                ).choices[0].message
                messages = [prompt_message, memory, summary_message] + messages[-7:]
            except:
                summary_message = client.chat.completions.create(
                    model=model,
                    messages=messages[2:-8] + [summary_prompt],
                ).choices[0].message
                messages = [prompt_message, memory, summary_message] + messages[-8:]
            '''
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

    st.rerun()
