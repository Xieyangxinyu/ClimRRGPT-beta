import streamlit as st
from src.llms import OpenSourceModels
from src.utils import stream_static_text, load_config
from st_pages import add_page_title
import json
from src.modules.experience.util import format_to_json
import re

add_page_title(initial_sidebar_state="collapsed", layout="wide")

st.session_state.config = load_config("./src/modules/experience/goal_setting.yml")
available_datasets = load_config("./src/modules/experience/dataset_description.yml")['available_datasets']
get_response = OpenSourceModels(model=st.session_state.config['model']).get_response

def initialize_session_state():
    st.session_state.instruction_message = st.session_state.config["instruction_message"]
    if 'questions' not in st.session_state:
        st.session_state.questions = []
    if 'current_brainstorm_index' not in st.session_state:
        st.session_state.current_brainstorm_index = 0
    if 'questions_done' not in st.session_state:
        st.session_state.questions_done = False
    if 'goals_recommendation' not in st.session_state:
        st.session_state.goals_recommendation = []
    if 'custom_goals' not in st.session_state:
        st.session_state.custom_goals = ["", "", ""]
    if 'goals_saved' not in st.session_state:
        st.session_state.goals_saved = False

def stream_handler(stream):
    response = ''
    keys=['Goal1', 'Goal2', 'Goal3', 'goal1', 'goal2', 'goal3', 'Goal 1', 'Goal 2', 'Goal 3']
    number_of_keys_hit = 0
    keys_hit = []
    progress_bar = st.progress(0)
    for chunk in stream:
        response += chunk['message']['content']
        for key in keys:
            if key in response and key not in keys_hit:
                number_of_keys_hit += 1
                keys_hit.append(key)
                progress_bar.progress(number_of_keys_hit / 3)
    return response

def parse_goals(response):
    print(response)
    try:
        json_match = re.search(r'```json\s*([\s\S]*?)\s*```', response)
        if not json_match:
            json_match = re.search(r'```\s*([\s\S]*?)\s*```', response)
        if json_match:
            json_string = json_match.group(1)
            parsed_data = json.loads(json_string)
        else:
            return []
    except json.JSONDecodeError:
        print("Invalid JSON format.")
        return []
    
    if type(parsed_data) is list:
        parsed_data = parsed_data[0]
    if type(parsed_data) is not dict:
        return []

    valid_entries = []
    for entry in parsed_data:
        if entry in ["Goal1", "Goal2", "Goal3", "goal1", "goal2", "goal3", "Goal 1", "Goal 2", "Goal 3"]:
            valid_entries.append(parsed_data[entry])
    if len(valid_entries) < 3:
        return []
    
    return valid_entries

if ("profile_done" not in st.session_state) or not st.session_state.profile_done:
    st.write(st.session_state.config["profile_not_complete_message"])
    if st.button("Complete My Profile"):
        st.switch_page("experience/profile.py")
elif not "questions_done" in st.session_state or not st.session_state.questions_done:
        st.write(st.session_state.config["questions_not_done_message"])
        if st.button("Identify Questions to Investigate From Scientific Literature"):
            st.switch_page("experience/question_identification.py")
else:
    initialize_session_state()

    if st.session_state.goals_saved:
        st.balloons()
        st.write(st.session_state.config['goal_saved_message'])
        for i, goal in enumerate(st.session_state.custom_goals):
            if goal:
                st.info(goal)
                st.write("")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Edit Goals", use_container_width=True):
                st.session_state.goals_saved = False
                st.rerun()
        with col2:
            if st.button("Let's Move On", use_container_width=True):
                st.switch_page("experience/data_visualization.py")
    if not st.session_state.goals_saved:
        st.write(st.session_state.config["welcome_message"])
        with st.expander("Instructions"):
            st.write(st.session_state.instruction_message)

        messages = []

        col1, col2 = st.columns([1,2])
        with col1:
            # list the profile
            st.write("### Profile")
            profile_text = ""
            items = list(st.session_state.responses.items())
            for key, value in items:
                st.markdown(f"**{key}**: {value}")
                profile_text += f"{key}: {value}\n"
            messages.append({"role": "user", "content": "I have the following profile:\n" + profile_text})

        with col2:
            # list the datasets to analyze
            st.write("### Datasets to Analyze")
            chosen_datasets = {}
            for dataset in st.session_state.selected_datasets:
                with st.expander(dataset, expanded=False):
                    st.markdown(f"**Description:** {available_datasets[dataset]['description']}")
                    st.markdown(f"**Instruction:** {available_datasets[dataset]['instruction']}")
                    
                chosen_datasets[dataset] = {key: available_datasets[dataset][key] for key in ["description", "instruction"]}
            messages.append({"role": "user", "content": f"I have chosen the following datasets to analyze:{format_to_json([chosen_datasets])}"})
            
            # list the questions
            st.write("### Questions to Investigate")
            questions_text = ""
            for question in st.session_state.questions:
                st.write(f"- {question}")
                questions_text += f"- {question}\n"
            messages.append({"role": "user", "content": "I have chosen the following questions to investigate from scientifi literature:\n" + questions_text})

            template = format_to_json([{
                "Goal1": "...",
                "Goal2": "...",
                "Goal3": "...",
            }])

            messages.append({"role": "user", "content": f"Suggest a list of 3 goals that I can work on to achieve my goal with the datasets and questions I have chosen. Focus on my profile. Each goal should be a specific task in one sentence. Because this is an exploratory project, I cannot make any projections or predictions. Please focus on delivering insights and recommendations. Output in a JSON format using this template:\n\n{template}"})
        
        st.write("### Goals to Achieve")

        # Initialize session state for custom goals if not already present
        

        # Create a form for custom goals
        with st.form(key='custom_goals_form'):
            for i in range(3):
                st.session_state.custom_goals[i] = st.text_input(f"Goal {i+1}", value=st.session_state.custom_goals[i])
            col1, col2 = st.columns(2)
            submit_form = st.form_submit_button(label='Save Goals')
        
        if submit_form:
            if not all(st.session_state.custom_goals):
                st.warning("Please fill in all three goals.")
            else:
                st.success("Your goals have been saved!")
                st.session_state.goals_saved = True
                st.rerun()
        
        col1, col2 = st.columns([1,3])
        with col1:
            if st.button("Get AI Recommendations"):
                with st.spinner("AI magic in action! 🧠⚡️ Please do not click any buttons on the sidebar or refresh the page."):
                    response = get_response(messages=messages, stream_handler=stream_handler,
                            stream=True, 
                            options={"top_p": 0.95, "max_tokens": 256, "temperature": 0.7}
                        )
                    # parse the response into the introduction passage and the JSON list
                        
                    st.session_state.goals_recommendation = parse_goals(response)
                    while len(st.session_state.goals_recommendation) == 0:
                        response = get_response(messages=messages, stream_handler=stream_handler,
                            options={"top_p": 0.95, "max_tokens": 256, "temperature": 0.7}
                        )
                        st.session_state.goals_recommendation = parse_goals(response)
        
        if st.session_state.goals_recommendation:
            with col2:
                st.write("#### AI Recommendations")
                if st.session_state.goals_recommendation:
                    for goal in st.session_state.goals_recommendation:
                        col_1, col_2 = st.columns([5, 1])
                        with col_1:
                            st.markdown(f"- {goal}")
                        with col_2:
                            if st.button("Use Suggested Goal", key=f"use_suggested_{st.session_state.goals_recommendation.index(goal)}", use_container_width=False):
                                st.session_state.custom_goals[st.session_state.goals_recommendation.index(goal)] = goal
                                st.rerun()