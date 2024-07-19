import streamlit as st
from src.utils import load_config
from src.llms import OpenSourceModels
from st_pages import add_page_title

add_page_title(initial_sidebar_state="collapsed")

st.session_state.config = load_config("src/modules/experience/literature_review.yml")
model = st.session_state.config['model']
get_response = OpenSourceModels(model=model).get_response

st.write("Page under construction. Please check back later.")