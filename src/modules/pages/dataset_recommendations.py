import streamlit as st
from src.utils import load_config
from src.llms import OpenSourceModels
import json
from copy import deepcopy
import re
from st_pages import add_page_title

add_page_title(layout="wide", initial_sidebar_state="collapsed")

st.session_state.config = load_config("src/modules/pages/dataset_recommendations.yml")
available_datasets = load_config("./src/modules/pages/dataset_description.yml")['available_datasets']
model = st.session_state.config['model']
get_response = OpenSourceModels(model=model).get_response

# only keep description and instructions of each dataset

def initialize_session_state():
    if 'dataset_recommendation' not in st.session_state:
        st.session_state.dataset_recommendation = None
    if 'selected_datasets' not in st.session_state:
        st.session_state.selected_datasets = []
    if 'ai_analysis_complete' not in st.session_state:
        st.session_state.ai_analysis_complete = False
    if 'skipped_recommendations' not in st.session_state:
        st.session_state.skipped_recommendations = False

def parse_dataset_recommendation(response, valid_keywords=available_datasets.keys()):
    # check if all four keywords are in the list
    try:
        json_match = re.search(r'```json\s*([\s\S]*?)\s*```', response)
        if json_match:
            json_string = json_match.group(1)
            parsed_data = json.loads(json_string)
        else:
            return []
    except json.JSONDecodeError:
        print("Invalid JSON format.")
        return []
    
    valid_entries = []
    
    for entry in parsed_data:
        if all(key in entry for key in ["dataset", "relevance", "explanation"]):
            if entry["dataset"] in valid_keywords:
                valid_entries.append(entry)
    
    return valid_entries

def stream_handler(stream):
    response = ''
    keys=available_datasets.keys()
    number_of_keys_hit = 0
    keys_hit = []
    progress_bar = st.progress(0)
    for chunk in stream:
        response += chunk['message']['content']
        for key in keys:
            if key in response and key not in keys_hit:
                number_of_keys_hit += 1
                keys_hit.append(key)
                details = available_datasets[key]
                progress_bar.progress(number_of_keys_hit / len(keys))
                with st.expander(key, expanded=False):
                    st.markdown(f"**Description:** {details['description']}")
                    st.markdown(f"**Instruction:** {details['instruction']}")
    return response

def get_dataset_recommendations():
    # Simulate AI processing
    with st.spinner("AI is analyzing which datasets to choose... Please do not click any buttons on the sidebar or refresh the page. In the meantime, AI will provide you with the description of each dataset it is considering."):
        available_datasets = load_config("./src/modules/pages/dataset_description.yml")['available_datasets']
        keywords = available_datasets.keys()
        available_datasets = {key: value['description'] + ' ' + value['instruction'] for key, value in available_datasets.items()}
        dataset_details = json.dumps(available_datasets, indent=4)

        messages = deepcopy(st.session_state.messages)
        
        messages = deepcopy(st.session_state.messages)
        dataset_recommendation_instructions = st.session_state.config['dataset_recommendation_instructions']
        messages[0]['content'] = dataset_recommendation_instructions[0]['content'].format(keywords=', '.join(keywords))
        messages.append({"role": "assistant", "content": dataset_recommendation_instructions[1]['content'].format(keywords=', '.join(keywords), dataset_details=dataset_details)})
        messages.append({"role": "user", "content": dataset_recommendation_instructions[2]['content']})

        response = get_response(messages=messages,
            stream=True, stream_handler=stream_handler,
            options={"top_p": 0.95, "max_tokens": 256, "temperature": 0.7}
        )

        # parse the response into the introduction passage and the JSON list
        
        st.session_state.dataset_recommendation = parse_dataset_recommendation(response)
        while len(st.session_state.dataset_recommendation) == 0:
            response = get_response(messages=messages,
                options={"top_p": 0.95, "max_tokens": 256, "temperature": 0.7}
            )
            st.session_state.dataset_recommendation = parse_dataset_recommendation(response)
        
        st.success("AI Analysis Complete!")

if ("profile_done" not in st.session_state) or not st.session_state.profile_done:
    st.write(st.session_state.config["profile_not_complete_message"])
    if st.button("Complete My Profile"):
        st.switch_page("pages/profile.py")
else:
    st.markdown(st.session_state.config['welcome_message'])
    with st.expander("Instructions"):
        st.write(st.session_state.config['instruction_message'])
    st.write("---")
    # Create two columns
    initialize_session_state()
    if not st.session_state.ai_analysis_complete:
        col1, col2 = st.columns([2,1])
        with col1:
            if st.button("Get AI Recommendations"):
                get_dataset_recommendations()
        with col2:
            if st.button("Skip AI Recommendations"):
                st.session_state.dataset_recommendation = []
                st.session_state.ai_analysis_complete = True
    
    if st.session_state.dataset_recommendation and not st.session_state.ai_analysis_complete:
        if st.button("Check AI Recommendations"):
            st.session_state.ai_analysis_complete = True
            st.rerun()
    
    col1, col2 = st.columns([2,1])
    if st.session_state.ai_analysis_complete:
        with col1:
            relevance_colors = {
                "High": "#FF4B4B",
                "Medium": "#9C27B0",
                "Low": "#795548"
            }
            st.markdown("Need to go over the dataset descriptions again? Click the `Available Datasets` button on the sidebar. 👈")
            if len(st.session_state.dataset_recommendation) == 0:
                st.warning("No dataset recommendations available.")
            else:
                st.subheader("AI Recommended Datasets:")
                for entry in st.session_state.dataset_recommendation:
                    with st.expander(entry["dataset"], expanded=(entry['relevance'].lower() == 'high')):
                        st.markdown(f"**Relevance:** <span style='color:{relevance_colors.get(entry['relevance'], 'black')}'>{entry['relevance']}</span>", unsafe_allow_html=True)
                        st.markdown(entry["explanation"])
        with col2:
            st.header("Selected Datasets")
            selected_datasets = st.multiselect(
                "Choose datasets for your analysis:",
                options=list(available_datasets.keys()),
                default=st.session_state.selected_datasets,
            )
            if selected_datasets:
                st.success(f"You've selected {len(selected_datasets)} dataset(s).")
                if st.button("Proceed to Goal Setting", type="primary"):
                    st.session_state.selected_datasets = selected_datasets
                    st.switch_page("pages/question_identification.py")
            else:
                st.info("Select at least one dataset to proceed.")