import streamlit as st
from src.utils import load_config
from src.llms import OpenSourceModels
from st_pages import add_page_title
from src.literature.search import literature_search

add_page_title(initial_sidebar_state="collapsed", layout="wide")

st.session_state.config = load_config("src/modules/experience/literature_review.yml")
model = st.session_state.config['model']
get_response = OpenSourceModels(model=model).get_response

# st.session_state.goals_saved = True
# st.session_state.selected_datasets = ['Fire Weather Index (FWI) projections', 'Seasonal Temperature Maximum projections', 'Precipitation projections']
# st.session_state.questions = ["How do changes in wildfire risk perception and public policy influence property values in areas susceptible to wildfires?", "How have historical wildfire events and subsequent property value changes in similar metropolitan areas influenced policy decisions regarding infrastructure mitigation strategies?"]
# st.session_state.custom_goals = ["Analyze the historical trends of FWI in Denver, CO and identify areas with significant increases or decreases in fire risk.",
#     "Investigate scientific literature to understand how changes in wildfire risk perception and public policy have affected property values in areas similar to Denver.",
#     "Explore the relationship between changes in wildfire risk (as reflected by FWI projections) and current property value assessments and insurance premiums in different areas of Denver."]
# st.session_state.responses= {
#     "Location": "Denver, CO",
#     "Profession": "Risk Manager",
#     "Concern": "Property values",
#     "Timeline": "30 - 50 years",
#     "Scope": "changes might affect property values in different areas based on their proximity to fire risk zones and existing infrastructure mitigation strategies."
# }
# st.session_state.questions_done = True
# st.session_state.goals_saved = True

st.session_state.config = load_config("src/modules/experience/literature_review.yml")


if ('questions_done' not in st.session_state) or (not st.session_state.questions_done):
    if st.button("Identify Questions"):
        st.switch_page("experience/question_identification.py")
else:
    st.write(st.session_state.config["welcome_message"])
    with st.expander("Instructions"):
        st.write(st.session_state.config["instruction_message"])

    if "literature_review_summary" in st.session_state:
        for i in range(2):
            st.markdown(f"#### Question: {i+1}")
            st.write(f"**{st.session_state.questions[i]}**")
            with st.expander("Show Literature Search Results"):
                st.write(st.session_state.retrieved_literature[i])
            st.write(st.session_state.literature_review_summary[i])
    else:
        st.session_state.retrieved_literature = []
        st.session_state.literature_review_summary = []
        for i in range(2):
            st.markdown(f"#### Question: {i+1}")
            st.write(f"**{st.session_state.questions[i]}**")
            retrieved_literature = literature_search(st.session_state.questions[i])
            st.session_state.retrieved_literature.append(retrieved_literature)
            with st.expander("Show Literature Search Results"):
                st.write(st.session_state.retrieved_literature[i])
            messages = [
                {"role": "system", "content": st.session_state.config["literature_review_instructions"][0]['content'].format(retrieve_literature = retrieved_literature)}, 
                {"role": "user", "content": f"Here is my profile:\n\nProfession: {st.session_state.responses['Profession']}\n\nConcern: {st.session_state.responses['Concern']}\n\nLocation: {st.session_state.responses['Location']}\n\nTimeline: {st.session_state.responses['Timeline']}\n\nScope: {st.session_state.responses['Scope']}"},
                {"role": "user", "content": st.session_state.questions[i]},
            ]
            st.session_state.literature_review_summary.append(
                get_response(messages=messages, stream=True,
                    options={"top_p": 0.9, "max_tokens": 1024, "temperature": 0.2}
                )
            )
        st.rerun()