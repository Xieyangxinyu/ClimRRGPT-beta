import streamlit as st
from src.utils import load_config
from src.llms import OpenSourceModels
import json
from copy import deepcopy
import re
from st_pages import add_page_title
from src.modules.experience.util import format_to_json

add_page_title(layout="wide", initial_sidebar_state="collapsed")

st.session_state.config = load_config("src/modules/experience/dataset_recommendations.yml")
available_datasets = load_config("./src/modules/experience/dataset_description.yml")['available_datasets']
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
            if entry["dataset"] in valid_keywords and entry["relevance"].lower() in ["high", "medium", "low"]:
                entry["relevance"] = entry["relevance"].capitalize()
                valid_entries.append(entry)
            else:
                # look to see if any of the keywords are in the dataset name
                for keyword in valid_keywords:
                    if keyword in entry["dataset"]:
                        valid_entries.append(entry)
                        break
    
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

def get_single_dataset_recommendation(dataset_name, dataset_details, recommendations):
    messages = deepcopy(st.session_state.messages)
    dataset_recommendation_instructions = st.session_state.config['dataset_recommendation_instructions']
    
    messages[0]['content'] = dataset_recommendation_instructions[0]['content'].format(keywords=dataset_name)
    if len(recommendations) > 0:
        messages.append(
            {"role": "assistant",
                "content": dataset_recommendation_instructions[3]['content'].format(keywords=dataset_name, 
                                                                                    dataset_recommendations=format_to_json(recommendations))}
        )
    messages.append(
        {"role": "assistant", 
         "content": dataset_recommendation_instructions[1]['content'].format(keywords=dataset_name, 
                                                                             dataset_details=
                                                                             format_to_json([{dataset_name: dataset_details}]))})
    messages.append({"role": "user", "content": dataset_recommendation_instructions[2]['content']})

    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = get_response(messages=messages, 
                options={"top_p": 0.8, "max_tokens": 256, "temperature": 0.5}
            )
            recommendation = parse_dataset_recommendation(response, valid_keywords=[dataset_name])
            if recommendation:
                return recommendation
        except Exception as e:
            st.warning(f"Oops! We hit a snag while processing {dataset_name} (Attempt {attempt + 1}/{max_retries}). We're trying again!")
    
    # If all attempts fail, return a friendly message with the suggestion
    st.error(f"We couldn't generate a recommendation for {dataset_name} at this time. Don't worry, though!")
    return [{
        "dataset": dataset_name,
        "relevance": "To be determined",
        "explanation": "We encountered a hiccup while analyzing this dataset. 🤔 No worries! You can still explore it yourself. Need to go over the dataset descriptions? Click the `Available Datasets` button on the sidebar. 👈 Your insights might be just what we need!"
    }]

def get_dataset_recommendations():
    available_datasets = load_config("./src/modules/experience/dataset_description.yml")['available_datasets']
    
    recommendations = []
    progress_bar = st.progress(0)
    
    for i, (dataset_name, dataset_info) in enumerate(available_datasets.items()):
        with st.expander(dataset_name, expanded=False):
            st.markdown(f"**Description:** {dataset_info['description']}")
            st.markdown(f"**Instruction:** {dataset_info['instruction']}")
        
        # dataset_details = dataset_info with only description and instruction
        dataset_details = {key: dataset_info[key] for key in ["description", "instruction"]}
        recommendation = get_single_dataset_recommendation(dataset_name, dataset_details, recommendations)
        
        recommendations.extend(recommendation)
        
        progress_bar.progress((i + 1) / len(available_datasets))

    # order the recommendations by relevance: From "High" to "Medium" to "Low"

    recommendations = sorted(recommendations, key=lambda x: ["High", "Medium", "Low"].index(x["relevance"]))

    st.session_state.dataset_recommendation = recommendations
    st.success("AI Analysis Complete!")

if ("profile_done" not in st.session_state) or not st.session_state.profile_done:
    st.write(st.session_state.config["profile_not_complete_message"])
    if st.button("Complete My Profile"):
        st.switch_page("experience/profile.py")
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
                    st.switch_page("experience/question_identification.py")
            else:
                st.info("Select at least one dataset to proceed.")