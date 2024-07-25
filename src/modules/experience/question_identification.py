import streamlit as st
from src.utils import load_config, stream_static_text
from src.llms import OpenSourceModels
from copy import deepcopy
from st_pages import add_page_title
import re

add_page_title(initial_sidebar_state="collapsed")

st.session_state.config = load_config("src/modules/experience/question_identification.yml")
available_datasets = load_config("./src/modules/experience/dataset_description.yml")['available_datasets']
model = st.session_state.config['model']
get_response = OpenSourceModels(model=model).get_response

def initialize_session_state():
    if 'suggested_question' not in st.session_state:
        st.session_state.suggested_question = [None, None]
    if 'instruction_message' not in st.session_state:
        st.session_state.instruction_message = st.session_state.config["instruction_message"]
    if 'questions' not in st.session_state:
        st.session_state.questions = []
    if 'current_brainstorm_index' not in st.session_state:
        st.session_state.current_brainstorm_index = 0
    if 'questions_done' not in st.session_state:
        st.session_state.questions_done = False
    elif st.session_state.questions_done:
        st.session_state.instruction_message = ""
    messages = deepcopy(st.session_state.messages)
    question_recommendation_instructions = st.session_state.config["question_recommendation_instructions"]
    messages[0]["content"] = question_recommendation_instructions[0]['content']

    messages.append({"role": "user", "content": "I have chosen the following datasets to analyze: " + "\n\n".join(f"**{dataset}**: {available_datasets[dataset]['description']}\n{available_datasets[dataset]['instruction']}" for dataset in st.session_state.selected_datasets)})
    messages.append({"role": "user", "content": question_recommendation_instructions[1]['content']})
    return messages, question_recommendation_instructions

def parse_question(response):
    if "?" not in response:
        return None
    response = re.sub(r"^\d+[.)]?\s*", "", response)
    return response

def get_question_suggestion(messages):
    for i in range(st.session_state.current_brainstorm_index):
        messages.append({"role": "assistant", "content": question_recommendation_instructions[i + 1]['content']})
    response = parse_question(get_response(messages=messages, stream=True,
        options={"top_p": 0.95, "max_tokens": 256, "temperature": 1, "stop": ["\n"]}
    ))
    # retry at most 3 times
    for i in range(3):
        while not response:
            stream_static_text("Sorry that wasn't a good question. Let me try again!")
            response = parse_question(get_response(messages=messages, stream=True,
                options={"top_p": 0.95, "max_tokens": 256, "temperature": 1, "stop": ["\n"]}
            ))
    if not response:
        response = "I'm sorry, I couldn't generate a question for you. Please try again later."
    return response

if ("profile_done" not in st.session_state) or not st.session_state.profile_done:
    st.write(st.session_state.config["profile_not_complete_message"])
    if st.button("Complete My Profile"):
        st.switch_page("experience/profile.py")
elif not "selected_datasets" in st.session_state or len(st.session_state.selected_datasets) == 0:
        st.write(st.session_state.config["datasets_not_selected_message"])
        if st.button("Select Datasets"):
            st.switch_page("experience/dataset_recommendations.py")
else:
    messages, question_recommendation_instructions = initialize_session_state()
    if len(st.session_state.instruction_message) > 0:
        st.write(st.session_state.config["welcome_message"])
        with st.expander("Instructions"):
            st.write(st.session_state.config["instruction_message"])

    if not st.session_state.questions_done:
        current_question = st.session_state.questions[st.session_state.current_brainstorm_index] if st.session_state.current_brainstorm_index < len(st.session_state.questions) else ""
        st.write(f"**Question {st.session_state.current_brainstorm_index + 1}:**")
        question = st.text_area("Your Question:", value=current_question, key=f"question_{st.session_state.current_brainstorm_index}",
                                label_visibility="collapsed")
        
        col1, col2, col3 = st.columns([1,2,2])
        
        with col1:
            if st.session_state.current_brainstorm_index > 0:
                if st.button("Previous", use_container_width=True):
                    st.session_state.current_brainstorm_index -= 1
                    st.rerun()
        
        with col2:
            if st.session_state.current_brainstorm_index < 1:
                if st.button("Next", use_container_width=True):
                    if question:
                        if st.session_state.current_brainstorm_index < len(st.session_state.questions):
                            st.session_state.questions[st.session_state.current_brainstorm_index] = question
                        else:
                            st.session_state.questions.append(question)
                        st.session_state.current_brainstorm_index += 1
                    st.rerun()
            else:
                if st.button("Finish", use_container_width=True):
                    if question:
                        if st.session_state.current_brainstorm_index < len(st.session_state.questions):
                            st.session_state.questions[st.session_state.current_brainstorm_index] = question
                        else:
                            st.session_state.questions.append(question)
                        st.session_state.questions_done = True
                        st.session_state.instruction_message = ""
                        st.session_state.suggested_question[st.session_state.current_brainstorm_index] = [None, None]
                    st.rerun()
        
        with col3:
            suggestions_needed = st.button("Generate Question Suggestion", use_container_width=True)

        if suggestions_needed:
            with st.spinner("Generating question suggestion..."):
                with st.chat_message("assistant"):
                    stream_static_text("Here is a question suggestion for you:")
                    response = get_question_suggestion(messages)
                    st.session_state.suggested_question[st.session_state.current_brainstorm_index] = response
                    st.rerun()
        
        if st.session_state.suggested_question[st.session_state.current_brainstorm_index]:
            with st.chat_message("assistant"):
                st.write("Here is a question suggestion for you:")
                st.write(st.session_state.suggested_question[st.session_state.current_brainstorm_index])

    if st.session_state.questions_done:
        st.write("## Questions to Investigate:")
        for i, question in enumerate(st.session_state.questions):
            st.write(f"{i+1}. {question}")
        
        col1, col2 = st.columns([1,1])
        with col1:
            if st.button("Edit Questions", use_container_width=True):
                st.session_state.questions_done = False
                st.session_state.current_brainstorm_index = 0
                st.session_state.instruction_message = st.session_state.config["instruction_message"]
                st.rerun()
        
        with col2:
            if st.button("Proceed to Goal Setting", use_container_width=True):
                # Add code here to move to the next step (e.g., literature review)
                del st.session_state['instruction_message']
                st.switch_page("experience/goal_setting.py")