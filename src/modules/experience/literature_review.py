import streamlit as st
from src.utils import load_config
from src.llms import OpenSourceModels
from st_pages import add_page_title
from src.literature.search import literature_search

add_page_title(initial_sidebar_state="collapsed", layout="wide")

st.session_state.config = load_config("src/modules/experience/literature_review.yml")
model = st.session_state.config['model']
get_response = OpenSourceModels(model=model).get_response


st.session_state.selected_datasets = ['Fire Weather Index (FWI) projections', 'Seasonal Temperature Maximum projections', 'Precipitation projections']
st.session_state.questions = ["How do changes in wildfire risk perception and public policy influence property values in areas susceptible to wildfires?", "How have historical wildfire events and subsequent property value changes in similar metropolitan areas influenced policy decisions regarding infrastructure mitigation strategies?"]
st.session_state.custom_goals = ["Analyze the historical trends of FWI in Denver, CO and identify areas with significant increases or decreases in fire risk.",
    "Investigate scientific literature to understand how changes in wildfire risk perception and public policy have affected property values in areas similar to Denver.",
    "Explore the relationship between changes in wildfire risk (as reflected by FWI projections) and current property value assessments and insurance premiums in different areas of Denver."]
st.session_state.responses= {
    "Location": "Denver, CO",
    "Profession": "Risk Manager",
    "Concern": "Property values",
    "Timeline": "30 - 50 years",
    "Scope": "changes might affect property values in different areas based on their proximity to fire risk zones and existing infrastructure mitigation strategies."
}
st.session_state.questions_done = True
st.session_state.profile_done = True


st.session_state.config = load_config("src/modules/experience/literature_review.yml")
if "qa_messages" not in st.session_state:
    st.session_state.qa_messages = []
    st.session_state.context = [
        {"role": "user", "content": f"Here is my profile:\n\nProfession: {st.session_state.responses['Profession']}\n\nConcern: {st.session_state.responses['Concern']}\n\nLocation: {st.session_state.responses['Location']}\n\nTimeline: {st.session_state.responses['Timeline']}\n\nScope: {st.session_state.responses['Scope']}"},
        {"role": "user", "content": f"Let's review these datasets:\n\n{[st.session_state.selected_datasets[i] for i in range(len(st.session_state.selected_datasets))]}"},
    ]
    if "analysis" in st.session_state:
        st.session_state.context.append({"role": "assistant", "content": st.session_state.analysis})
    if "data_analysis_summary" in st.session_state:
        st.session_state.context.append({"role": "assistant", "content": st.session_state.data_analysis_summary})


if ('questions_done' not in st.session_state) or (not st.session_state.questions_done):
    if st.button("Identify Questions"):
        st.switch_page("experience/question_identification.py")
else:
    st.write(st.session_state.config["welcome_message"])
    with st.expander("Instructions"):
        st.write(st.session_state.config["instruction_message"])

    if "literature_review_summary" in st.session_state:
        st.markdown(f"#### Question (s):")
        for i in range(len(st.session_state.questions)):
            st.write(f"**{st.session_state.questions[i]}**")
            with st.expander("Show Literature Search Results"):
                st.write(st.session_state.retrieved_literature[i])
        st.write(st.session_state.literature_review_summary)

        st.markdown("------------------------------------")
        st.markdown("#### Chat with Literature Review Assistant")

        for message in st.session_state.qa_messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
        if prompt := st.chat_input("How can I help you?"):
            # Display user message in chat message container
            st.chat_message("user").markdown(prompt)
            # Add user message to chat history

            st.session_state.qa_messages.append({"role": "user", "content": prompt})

            # Display assistant response in chat message container
            with st.chat_message("assistant"):
                response = get_response(messages=st.session_state.context + st.session_state.qa_messages, stream=True, 
                    options={"top_p": 0.9, "max_tokens": 2048, "temperature": 0.7}
                )
            # Add assistant response to chat history
            st.session_state.qa_messages.append({"role": "assistant", "content": response})

    else:
        st.session_state.retrieved_literature = []
        
        st.session_state.references = []

        if st.session_state.questions[1] == "":
            # remove the second question if it is empty
            st.session_state.questions.pop(1)
        
        st.markdown(f"#### Question (s):")

        with st.spinner("AI in action! Please do not click any buttons or refresh the page."):
            for i in range(len(st.session_state.questions)):
                st.write(f"**{st.session_state.questions[i]}**")
                retrieved_literature, references = literature_search(st.session_state.questions[i])
                with st.expander("Show Literature Search Results"):
                    st.write(retrieved_literature)
                st.session_state.retrieved_literature.append(retrieved_literature)
                st.session_state.references += references
        
        st.session_state.context.append({"role": "system", "content": f"Here are the reference papers: {(retrieve_literature := st.session_state.retrieved_literature)}."})

        st.session_state.generate_summary = st.button("Generate Summary", use_container_width=True)

        if st.session_state.generate_summary:
            messages = [
                {"role": "system", "content": st.session_state.config["literature_review_instructions"][0]['content'].format(retrieve_literature = st.session_state.retrieved_literature)}
            ]
            st.session_state.context.append({"role": "user", "content": f"Here are my questions:\n\n{[st.session_state.questions[i] for i in range(len(st.session_state.questions))]}"})

            messages = st.session_state.context + messages

            st.session_state.literature_review_summary = get_response(messages=messages, stream=True,
                    options={"top_p": 0.9, "max_tokens": 2048, "temperature": 0.7, "stop": ["Works Cited\n", "References\n", "Bibliography\n"]}
                )
            if "Works Cited" in st.session_state.literature_review_summary:
                # remove the "Works Cited" section
                st.session_state.literature_review_summary = st.session_state.literature_review_summary.split("Works Cited")[0]
            if "References" in st.session_state.literature_review_summary:
                # remove the "References" section
                st.session_state.literature_review_summary = st.session_state.literature_review_summary.split("References")[0]
            if "Bibliography" in st.session_state.literature_review_summary:
                # remove the "Bibliography" section
                st.session_state.literature_review_summary = st.session_state.literature_review_summary.split("Bibliography")[0]

            # remove duplicates from the references
            st.session_state.references = list(dict.fromkeys(st.session_state.references))
            # sort the references
            st.session_state.references.sort()
            st.session_state.literature_review_summary += "\n\n### References:\n\n"
            for i in range(len(st.session_state.references)):
                st.session_state.literature_review_summary += f"{st.session_state.references[i]}\n\n"
            
            st.session_state.context.append({"role": "assistant", "content": st.session_state.literature_review_summary})
            st.rerun()