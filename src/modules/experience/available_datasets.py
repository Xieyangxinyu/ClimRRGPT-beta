import streamlit as st
from src.utils import load_config
from st_pages import add_page_title

add_page_title(layout="wide")

st.session_state.config = load_config("./src/modules/experience/dataset_description.yml")
available_datasets = st.session_state.config['available_datasets']

for dataset, details in available_datasets.items():
    
    # Using header and subheader for better visual hierarchy
    st.header(dataset)
    # Use markdown for rich text formatting and emphasis on certain elements
    st.markdown(f"**Description:** {details['description']}")
    st.markdown(f"**Instruction:** {details['instruction']}")
    
    # Check if there is a 'note' and display it if present
    if 'note' in details:
        st.markdown(f"**Note:** {details['note']}")
    
    st.subheader("Links")
    # Using an expander to save space and make the page cleaner
    with st.expander("See links"):
        for link in details["links"]:
            st.markdown(f"[{link['name']}]({link['url']})", unsafe_allow_html=True)
    
    st.markdown("---")  # Adding a separator for clarity