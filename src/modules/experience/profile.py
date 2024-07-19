import streamlit as st
from src.llms import OpenSourceModels
from src.utils import stream_static_text, load_config
from st_pages import add_page_title

add_page_title(initial_sidebar_state="collapsed")

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
    if 'instruction_message' not in st.session_state:
        st.session_state.instruction_message = instruction_message
    if 'profile_done' not in st.session_state:
        st.session_state.profile_done = False
    if 'current_question_index' not in st.session_state:
        st.session_state.current_question_index = 0
    if 'messages' not in st.session_state:
        st.session_state.messages = []
    if "responses" not in st.session_state:
        st.session_state.responses = {}

initialize_session_state()

if len(st.session_state.instruction_message) > 0:
    st.write(
        """
        We're about to craft a custom action plan just for you, but first, we need to know the hero of our story - YOU! 🌟🔥 
        
        Click the "Instructions" expander below to discover how to navigate this exciting journey! 
        """
    )
    with st.expander("Instructions"):
        st.write(st.session_state.instruction_message)
questions_list = list(questions.keys())

if not st.session_state.profile_done:
    current_key = questions_list[st.session_state.current_question_index]
    
    # Display current question
    st.markdown(questions[current_key])
    response = st.text_input(questions[current_key], 
                             value=st.session_state.responses.get(current_key, ""),
                             key=f"input_{current_key}", label_visibility = "collapsed")

    # Navigation buttons
    col1, col2, col3 = st.columns([1,2,2])
    with col1:
        if st.session_state.current_question_index > 0:
            if st.button("Previous", use_container_width=True):
                st.session_state.current_question_index -= 1
                st.rerun()
    
    with col2:
        if st.session_state.current_question_index < len(questions_list) - 1:
            next = st.button("Next", use_container_width=True)
            if next:
                if response:
                    st.session_state.responses[current_key] = response
                    if st.session_state.current_question_index < len(questions_list) - 1:
                        st.session_state.current_question_index += 1
                    st.rerun()
        else:
            if st.button("I'm Done with these Questions!", use_container_width=True):
                if response:
                    st.session_state.responses[current_key] = response
                else:
                    st.error("Please provide a response before proceeding.")
                if all(key in st.session_state.responses for key in questions_list):
                    st.session_state.instruction_message = ""
                    st.session_state.profile_done = True
                    st.session_state.messages = []
                    st.session_state.messages.append({"role": "system", "content": ""})
                    for key, value in st.session_state.responses.items():
                        st.session_state.messages.append({"role": "assistant", "content": questions[key]})
                        st.session_state.messages.append({"role": "user", "content": value})
                    st.rerun()

    with col3:
        suggestions_needed = st.button("Give me suggestions!", use_container_width=True)

    # "I'm Done" button
    

    # Suggestions logic (keep as is)
    if suggestions_needed:
        last_question = questions_list[st.session_state.current_question_index]
        with st.chat_message("assistant"):
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
                        options={"top_p": 0.95, "max_tokens": 64, "temperature": 0.7, "stop": ["\n", "?"]}
                    )

else:
    col1, col2 = st.columns(2)
    
    # Distribute the profile items across the two columns
    items = list(st.session_state.responses.items())
    
    for key, value in items:
        st.markdown(f"**{key}**")
        st.info(value)
        st.write("")  # Add some space between items
    
    st.markdown("---")  # Add a horizontal line for separation
    
    st.markdown("Congratulations! You have successfully completed your profile!")

    st.markdown("🚀 Now let's identify some datasets we can analyze together today. 🚀")
    # Add a button to jump to the goals page
    col1, col2  = st.columns(2)
    with col1:
        if st.button("Edit Profile", use_container_width=True):
            st.session_state.instruction_message = st.session_state.config['instruction_message']
            st.session_state.profile_done = False
            st.rerun()
    with col2:
        if st.button("Next Step", use_container_width=True):
            # remove the instruction message key from the session state
            del st.session_state['instruction_message']
            st.switch_page("experience/dataset_recommendations.py")
