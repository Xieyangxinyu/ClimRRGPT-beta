import streamlit as st
from src.llms import OpenSourceModels
from src.utils import stream_static_text, load_config
from st_pages import add_page_title

add_page_title(initial_sidebar_state="collapsed")

# Load config once
st.session_state.config = load_config("./src/modules/experience/profile.yml")

@st.cache_data
def load_config_wrapper():
    config = st.session_state.config
    questions = config['init_questions']
    suggestions = config['profile_suggestions']
    instruction_message = config['instruction_message']
    model = config['model']
    get_response = OpenSourceModels(model=model).get_response
    return questions, suggestions, instruction_message, get_response

questions, suggestions, instruction_message, get_response = load_config_wrapper()

def initialize_session_state():
    st.session_state.setdefault('instruction_message', instruction_message)
    st.session_state.setdefault('profile_done', False)
    st.session_state.setdefault('responses', {})

initialize_session_state()

if not st.session_state.profile_done:
    st.write("""
        We're about to craft a custom action plan just for you, but first, we need to know the hero of our story — YOU! 🌟🔥  
        Click the "Instructions" expander below to discover how to navigate this exciting journey!
    """)
    with st.expander("Instructions"):
        st.write(st.session_state.instruction_message)

    # Create a form to hold all questions
    with st.form("profile_form"):
        answers = {}
        for key, prompt in questions.items():
            # prefill with any existing value
            answers[key] = st.text_input(prompt,
                                         value=st.session_state.responses.get(key, ""),
                                         key=f"input_{key}")
        submitted = st.form_submit_button("Submit Profile")

    if submitted:
        missing = [k for k, v in answers.items() if not v.strip()]
        if missing:
            st.error("Please answer all questions before submitting.")
        else:
            # Save responses
            st.session_state.responses = answers
            # Build the chat history for downstream
            st.session_state.profile_done = True
            st.session_state.messages = [{"role": "system", "content": ""}]
            for key, value in st.session_state.responses.items():
                st.session_state.messages.append({"role": "assistant", "content": questions[key]})
                st.session_state.messages.append({"role": "user", "content": value})
            st.experimental_rerun()
    else:
        suggestions_needed = st.button("Give me suggestions!", use_container_width=True)
        if suggestions_needed:
            st.session_state.suggestions_needed = True
        if st.session_state.suggestions_needed:
            # ask the user to click which question they want to brainstorm
            st.session_state.last_question = st.selectbox("Which question do you want to brainstorm?", options=list(questions.keys()))
            with st.chat_message("assistant"):
                last_question = st.session_state.last_question
                stream_static_text(suggestions[last_question])
                if last_question == "Scope":
                        messages = [
                            {"role": "system", "content": "You are a helpful assistant. Your user is hoping to address their concern about wildfire risks and climate change by surveying existing scientific literatures. Please help with brainstorming some specific aspects of wildfire risks that they might be interested in exploring."},
                        ]
                        for key, value in st.session_state.responses.items():
                            messages.append({"role": "assistant", "content": questions[key]})
                            messages.append({"role": "user", "content": value})
                        
                        messages.append({"role": "assistant", "content": questions[last_question]})
                        messages.append({"role": "user", "content": "Could you provide some suggestions? Respond within a paragraph of at most 2 sentences."})
                        response = get_response(messages=messages, stream=True,
                            options={"top_p": 0.95, "max_tokens": 64, "temperature": 0.7, "stop": ["?"]}
                        )


else:
    # Display profile summary
    for key, value in st.session_state.responses.items():
        st.markdown(f"**{key}**")
        st.info(value)
        st.write("")  # spacing

    st.markdown("---")
    st.markdown("Congratulations! You have successfully completed your profile! 🚀")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Edit Profile", use_container_width=True):
            st.session_state.profile_done = False
            st.experimental_rerun()
    with col2:
        if st.button("Next Step", use_container_width=True):
            del st.session_state['instruction_message']
            st.switch_page("experience/dataset_recommendations.py")