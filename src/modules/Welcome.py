import streamlit as st
from st_pages import Page, Section, show_pages, add_page_title, hide_pages

add_page_title(initial_sidebar_state="collapsed")

# Specify what pages should be shown in the sidebar, and what their titles and icons
# should be
show_pages(
    [
        Page("src/modules/Welcome.py", "Welcome", "🔥"),
        Page("src/modules/pages/profile.py", "Profile", ":books:"),
        Section("Deliverables", icon="📝"),
        Page("src/modules/pages/dataset_recommendations.py", "Dataset Recommendations", "📈"),
        Page("src/modules/pages/question_identification.py", "Question Identification", "🎯"),
        Page("src/modules/pages/goal_setting.py", "Goal Setting", "🎯"),
        Section("Resouces", icon="🌐"),
        Page("src/modules/pages/available_datasets.py", "Available Datasets", "📈"),
        Section("Analysis", icon="🔍"),
        Page("src/modules/pages/data_visualization.py", "Data Visualization", "📈"),
    ]
)

# read welcome message from `welcome.md`
with open("src/modules/welcome.md", "r") as f:
    welcome_message = f.read()

# Display welcome message
st.markdown(welcome_message, unsafe_allow_html=True)

# Display the start button
col1, col2, col3 = st.columns([1,2,1])

with col2:
    if st.button("Start Your WildfireGPT Journey", use_container_width=True):
        st.switch_page("pages/profile.py")