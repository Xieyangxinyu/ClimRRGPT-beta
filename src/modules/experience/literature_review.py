import streamlit as st
from src.utils import load_config
from src.llms import OpenSourceModels
from st_pages import add_page_title
from src.literature.search import literature_search

add_page_title(initial_sidebar_state="collapsed")

st.session_state.config = load_config("src/modules/experience/literature_review.yml")
model = st.session_state.config['model']
get_response = OpenSourceModels(model=model).get_response

st.write("Page under construction. Please check back later.")


if ('questions_done' not in st.session_state) or (not st.session_state.questions_done):
    if st.button("Identify Questions"):
        st.switch_page("experience/question_identification.py")
elif ("goals_saved" not in st.session_state) or not st.session_state.goals_saved:
    #st.write(st.session_state.config[""])
    if st.button("Set Goals"):
        st.switch_page("experience/goal_setting.py")
else:
    st.markdown(f"#### First Question:")
    st.write(st.session_state.questions[0])
    st.markdown(f"#### Literature Search Results:")
    st.markdown(literature_search(st.session_state.questions[0]))

    st.markdown(f"#### Second Question:")
    st.write(st.session_state.questions[1])
    st.markdown(f"#### Literature Search Results:")
    st.markdown(literature_search(st.session_state.questions[1]))