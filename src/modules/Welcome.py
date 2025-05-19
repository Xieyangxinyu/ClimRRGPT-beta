import streamlit as st
from st_pages import Page, Section, show_pages, add_page_title, hide_pages

add_page_title(initial_sidebar_state="collapsed")

# Specify what experience should be shown in the sidebar, and what their titles and icons
# should be
show_pages(
    [
        Page("src/modules/Welcome.py", "Welcome", "🔥"),
        Page("src/modules/experience/profile.py", "Profile", ":books:"),
        Section("Deliverables", icon="📝"),
        Page("src/modules/experience/dataset_recommendations.py", "Dataset Recommendations", "📈"),
        Page("src/modules/experience/question_identification.py", "Question Identification", "🎯"),
        Page("src/modules/experience/goal_setting.py", "Goal Setting", "🎯"),
        Section("Resouces", icon="🌐"),
        Page("src/modules/experience/available_datasets.py", "Available Datasets", "📈"),
        Section("Analysis", icon="🔍"),
        Page("src/modules/experience/data_visualization.py", "Data Visualization", "📈"),
        Page("src/modules/experience/literature_review.py", "Literature Review", "📚"),
    ]
)

# read welcome message from `welcome.md`
with open("src/modules/welcome.md", "r") as f:
    instruction_message = f.read()

# Display welcome message

st.markdown("Get ready to ignite your understanding of hazard risks with ClimRRGPT!\n\nClimRRGPT guides you through understanding and addressing hazard risks, especially for assessing future risks in specific locations. ", unsafe_allow_html=True)
with st.expander("Here's your journey:"):
        st.markdown(instruction_message, unsafe_allow_html=True)

# Display the start button
col1, col2, col3 = st.columns([1,2,1])

with col2:
    if st.button("Start Your ClimRRGPT Journey", use_container_width=True):
        st.switch_page("experience/profile.py")