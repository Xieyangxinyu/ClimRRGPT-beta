from src.assistants.assistant_router import AssistantRouter
import streamlit as st
import clipboard
import json

st.title("Wildfire GPT")

def on_copy_click(text):
    st.session_state.copied.append(text)
    clipboard.copy(text)

def display_feedback(message, index):
    increment = 0
    if message["role"] == "assistant":
        like_key = f"like_{index}"
        dislike_key = f"dislike_{index}"
        feedback_key = f"feedback_{index}"
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
    

    st.session_state.checklist = '''
Profession: Risk manager.
Concern: High-intensity fire near Las Vegas, NM, and primary risk factors concerning wildfires.
Location: Sangre de Cristo Mountains.
Time: Immediate need for post-fire mitigation strategies.
Scope: Concerned about the impact on water supply.
'''
    st.session_state.plan = '''
Step 1: Analyze Recent Fire Incident Data We will analyze recent fire incident data to understand the frequency, size, location, and timing of wildfires in your area since this can provide insights into the current situation. This analysis helps us determine the immediate actions that need to be taken to mitigate risks effectively.
Step 2: Literature Search on Wildfire Mitigation and Water Supply Management I'll conduct a thorough literature search focusing on successful wildfire mitigation strategies implemented in regions with similar geographic and climatic conditions. This will also include studies on managing the water supply post-wildfires, which is a critical concern for your area.
Step 3: Recommendations for Immediate Post-Fire Mitigation Based on the insights gained from the recent fire data analysis and literature review, I will draft a set of tailored recommendations. These will focus on immediate and effective strategies for post-fire mitigation, emphasizing safeguarding the water supply and reducing future wildfire risks.
Step 4: Engage with Stakeholders I'll prepare a presentation of our findings and proposed strategies to engage with local stakeholders. This will ensure that the suggestions are practical and have the support needed for implementation.
'''
    st.session_state.assistant = AssistantRouter("AnalystAssistant", args={"checklist": st.session_state.checklist, "plan": st.session_state.plan})
    
    with st.chat_message("assistant"):
        full_response = st.session_state.assistant.get_assistant_response()
    st.session_state.messages.append({"role": "assistant", "content": full_response})
    st.rerun()


def display_reponse(message, index=0):
    with st.chat_message(message["role"]):
        response = message["content"]
        if type(response) != str:
            response, figs = response
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
    with st.chat_message("user"):
        st.markdown(user_prompt)
    
    st.session_state.messages.append({"role": "user", "content": user_prompt})

    with st.chat_message("assistant"):
        full_response = st.session_state.assistant.get_assistant_response(user_prompt)
    
    st.session_state.messages.append({"role": "assistant", "content": full_response})
    st.rerun()
