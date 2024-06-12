from src.assistants.assistant_router import AssistantRouter
import streamlit as st
import clipboard
import json
import pydeck as pdk

st.title("Wildfire GPT")

def on_copy_click(text):
    st.session_state.copied.append(text)
    clipboard.copy(text)

def display_feedback(message, index):
    increment = 0
    if message["role"] == "assistant":
        like_key = f"like_{index}"
        dislike_key = f"dislike_{index}"

        for feedback in ["Correctness", "Relevance", "Entailment", "Accessibility"]:
            feedback_key = f"{feedback}_{index}"
            if feedback_key not in st.session_state:
                st.session_state[feedback_key] = ""
        
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

        feedback_dict = {}

        for feedback in ["Correctness", "Relevance", "Entailment", "Accessibility"]:
            feedback_key = f"{feedback}_{index}"
            feedback_dict[feedback] = st.text_input(f"Feedback: {feedback}", key=feedback_key)
            if feedback_dict[feedback]:
                message[feedback.lower() + "_feedback"] = feedback_dict[feedback]

        increment = 1

    message_save = {k: v for k, v in message.items() if k != "content"}
    message_save["content"] = message["content"] if type(message["content"]) == str else message["content"][0]
    json.dump(message_save, file, indent=4, )
    return increment

if "copied" not in st.session_state: 
    st.session_state.copied = []
            

if "messages" not in st.session_state:
    st.session_state.messages = []
    st.session_state.thread_id = None
    #st.session_state.assistant = AssistantRouter("ChecklistAssistant")
    #with st.chat_message("assistant"):
    #    full_response = st.session_state.assistant.get_assistant_response()
    #st.session_state.messages.append({"role": "assistant", "content": full_response})

    checklist = '- Profession: Risk Manager\n- Concern: High intensity fire near Las Vegas, NM; primary risk factors to be concerned about.\n- Location: Sangre de Cristo Mountains \n- Time: Immediate measures to mitigate risks\n- Scope: Water resources and unpaved roads\n'
    args = {"checklist": checklist}
    st.session_state.assistant = AssistantRouter("PlanAssistant", thread_id='thread_jMbfylzr3eXZYSZNwPKspW7x', args=args)


    st.rerun()


def display_reponse(message, index=0):
    with st.chat_message(message["role"]):
        response = message["content"]
        if type(response) != str:
            response, visualizations = response
            for visualization in visualizations:
                maps, figs = visualization
                if type(maps) == pdk.Deck:
                    st.pydeck_chart(maps)
                for fig in figs:
                    st.plotly_chart(fig, use_container_width=True)
        st.markdown(response)
        return display_feedback(message, index)

index = 0
with open("chat_history/interaction.jsonl", "w") as file:
    for message in st.session_state.messages:
        like_key = f"like_{index}"
        dislike_key = f"dislike_{index}"
        index += display_reponse(message, index)

if user_prompt := st.chat_input("Ask me anything?"):
    if user_prompt.lower() == 'resume conversation':
        st.session_state.assistant.resume_conversation()
        user_prompt = None
        if len(st.session_state.messages) > 0 and st.session_state.messages[-1]['role'] == 'assistant':
            st.session_state.messages.pop(-1)
    else:
        with st.chat_message("user"):
            st.markdown(user_prompt)
        st.session_state.messages.append({"role": "user", "content": user_prompt})

    with st.chat_message("assistant"):
        full_response = st.session_state.assistant.get_assistant_response(user_prompt)
    
    st.session_state.messages.append({"role": "assistant", "content": full_response})
    st.rerun()
