from src.assistants.assistant_router import AssistantRouter
import streamlit as st
import clipboard
import json
import pydeck as pdk
import folium
from streamlit_folium import st_folium
import pickle

st.title("Wildfire GPT")

def on_copy_click(text):
    st.session_state.copied.append(text)
    clipboard.copy(text)

def display_feedback(message, index):
    increment = 0
    if message["role"] == "assistant":
        like_key = f"like_{index}"
        dislike_key = f"dislike_{index}"

        for feedback in ["Correctness", "Relevance", "Entailment", "Accessibility"]:
            feedback_key = f"{feedback}_{index}"
            if feedback_key not in st.session_state:
                st.session_state[feedback_key] = ""
        
        col1, col2, col3 = st.columns([1, 1, 2])
        # Render like button or indicate it's been pressed
        if st.session_state.get(like_key) or message.get("liked"):
            col1.success("Liked 👍")
            message["liked"] = True
            message["disliked"] = False
        else:
            if col1.button("👍", key=like_key):
                st.session_state[like_key] = True  # Mark as liked
                message["liked"] = True  # Mark as liked
                message["disliked"] = False  # Mark as not disliked

        # Similarly for dislike button
        if st.session_state.get(dislike_key) or message.get("disliked"):
            col2.error("Disliked 👎")
            message["liked"] = False  # Mark as not liked
            message["disliked"] = True
        else:
            if col2.button("👎", key=dislike_key):
                st.session_state[dislike_key] = True
                message["liked"] = False
                message["disliked"] = True
        col3.button("📋", on_click=on_copy_click, args=(message["content"],), key=index)

        feedback_dict = {}
        with st.expander("Click to provide feedback"):
            for feedback in ["Correctness", "Relevance", "Entailment", "Accessibility"]:
                if feedback == "Relevance":
                    with st.form(f"Relevance Feedback {index}"):
                        st.write("Relevance Feedback")
                        # Multiple choice question under Relevance
                        q1 = st.radio("Does my response answer your last question?", ["Yes", "No", "Could be better"])
                        q2 = st.radio("Is my response relevant to your profession?", ["Yes", "No", "Could be better"])
                        q3 = st.radio("Is my response relevant to your concern?", ["Yes", "No", "Could be better"])
                        q4 = st.radio("Is my response relevant to the location?", ["Yes", "No", "Could be better"])
                        q5 = st.radio("Is my response relevant to the timeline?", ["Yes", "No", "Could be better"])
                        q6 = st.radio("Is my response relevant to the scope?", ["Yes", "No", "Could be better"])

                        # Form submit button
                        submitted = st.form_submit_button("Submit")
                        if submitted:
                            st.write("Feedback submitted!")
                            message["relevance_feedback_q1"] = q1
                            message["relevance_feedback_q2"] = q2
                            message["relevance_feedback_q3"] = q3
                            message["relevance_feedback_q4"] = q4
                            message["relevance_feedback_q5"] = q5
                            message["relevance_feedback_q6"] = q6

                if feedback == "Entailment":
                    with st.form(f"Entailment Feedback {index}"):
                        st.write("Entailment Feedback")
                        # Multiple choice question under Entailment
                        q1 = st.radio("Are my analysis or recommendations logically following from the information (data, literature) provided?", ["Yes", "No", "Could be better"])

                        # Form submit button
                        submitted = st.form_submit_button("Submit")
                        if submitted:
                            st.write("Feedback submitted!")
                            message["entailment_feedback_q1"] = q1

                if feedback == "Accessibility":
                    with st.form(f"Accessibility Feedback {index}"):
                        st.write("Accessibility Feedback")
                        # Multiple choice question under Accessibility
                        q1 = st.radio("Does my response contain too many jargons?", ["Yes", "No", "Could be better"])
                        q2 = st.radio("Does my response provide enough explanation?", ["Yes", "No", "Could be better"])
                        q3 = st.radio("Does my response contain redundant or useless information?", ["Yes", "No", "Could be better"])

                        # Form submit button
                        submitted = st.form_submit_button("Submit")
                        if submitted:
                            st.write("Feedback submitted!")
                            message["accessibility_feedback_q1"] = q1
                            message["accessibility_feedback_q2"] = q2
                            message["accessibility_feedback_q3"] = q3
                feedback_key = f"{feedback}_{index}"
                feedback_dict[feedback] = st.text_input(f"{feedback} Feedback", key=feedback_key)
                if feedback_dict[feedback]:
                    message[feedback.lower() + "_feedback"] = feedback_dict[feedback]

        increment = 1

    message_save = {k: v for k, v in message.items() if k != "content"}
    message_save["content"] = message["content"] if type(message["content"]) == str else message["content"][0]
    json.dump(message_save, file, indent=4, )
    return increment

if "messages" not in st.session_state:
    # check if the session state variable can be loaded
    try:
        with open("chat_history/session_state.pkl", "rb") as file:
            data = pickle.load(file)
            for key in ["messages", "assistant", "location_confirmed", "copied", "lat", "lon"]:
                if key in data.keys():
                    st.session_state[key] = data[key]
    except:
        st.session_state.messages = []
        st.session_state.assistant = AssistantRouter("ChecklistAssistant")
        with st.chat_message("assistant"):
            full_response = st.session_state.assistant.get_assistant_response()
        st.session_state.messages.append({"role": "assistant", "content": full_response})
        st.session_state.location_confirmed = True
        st.session_state.copied = []

        #checklist = '- Profession: Risk Manager\n- Concern: High intensity fire near Las Vegas, NM; primary risk factors to be concerned about.\n- Location: Sangre de Cristo Mountains \n- Time: Immediate measures to mitigate risks\n- Scope: Water resources and unpaved roads\n'
        #args = {"checklist": checklist}
        #st.session_state.assistant = AssistantRouter("PlanAssistant", thread_id='thread_jMbfylzr3eXZYSZNwPKspW7x', args=args)
    st.rerun()
elif "messages" in st.session_state:
    with open("chat_history/session_state.pkl", "wb") as file:
        states = {}
        for key in ["messages", "assistant", "location_confirmed", "copied", "lat", "lon"]:
            if key in st.session_state.keys():
                states[key] = st.session_state[key]
        pickle.dump(states, file)

def display_reponse(message, index=0):
    with st.chat_message(message["role"]):
        response = message["content"]
        if type(response) != str:
            response, visualizations = response
            for visualization in visualizations:
                maps, figs = visualization
                if type(maps) == list and type(maps[1]) == pdk.Deck:
                    caption, maps = maps
                    st.write(caption)
                    st.pydeck_chart(maps)
                for fig in figs:
                    st.plotly_chart(fig, use_container_width=True)
        st.markdown(response)
        return display_feedback(message, index)

index = 0
with open("chat_history/interaction.jsonl", "w") as file:
    for message in st.session_state.messages:
        like_key = f"like_{index}"
        dislike_key = f"dislike_{index}"
        index += display_reponse(message, index)

if st.session_state.location_confirmed == False:
    lat = st.session_state.lat
    lon = st.session_state.lon
    st.write("The map below shows the initial location with 36km radius. Click on the map to select a location.")
    # Create a Folium map object
    m = folium.Map(location=[lat, lon], zoom_start=9)
    folium.Circle(
        location=[lat, lon],
        radius=36000,  # 36km in meters
        color='red',
        fill=True,
        fill_color='red',
        fill_opacity=0.2
    ).add_to(m)

    folium.Marker(location=[lat, lon], popup='Initial Location').add_to(m)
    # Add a click listener to the map
    m.add_child(folium.ClickForMarker(popup='Clicked Location'))
    m.add_child(folium.LatLngPopup())
    map = st_folium(m, height=350, width=700)

    try:
        data = (map['last_clicked']['lat'],map['last_clicked']['lng'])
        m2 = folium.Map(location=[lat, lon], zoom_start=9)
        folium.Marker(location=[lat, lon], popup='Initial Location').add_to(m2)
        folium.Circle(
            location=data,
            radius=36000,  # 36km in meters
            color='red',
            fill=True,
            fill_color='red',
            fill_opacity=0.2
        ).add_to(m2)
        st.write(f"Clicked Coordinates:{data}. The location, with radius 36km, has been shown on the map below. Please confirm the location by clicking the 'Confirm Location' button.")
        folium.Marker(location=[data[0], data[1]], popup='Initial Location').add_to(m2)
        st_folium(m2, height=350, width=700)
    except:
        data = [lat, lon]
        

    # Initialize a session state variable if not already set
    if 'location_confirmed' not in st.session_state:
        st.session_state.location_confirmed = False

    # Button to confirm the location
    if st.button("Confirm Location"):
        st.session_state.location_confirmed = True
        user_prompt = f"The location has been confirmed: latitude {data[0]}, longitude {data[1]}."
        with st.chat_message("user"):
            st.markdown(user_prompt)
        st.session_state.messages.append({"role": "user", "content": user_prompt})
        with st.chat_message("assistant"):
            full_response = st.session_state.assistant.get_assistant_response(user_prompt)
        st.session_state.messages.append({"role": "assistant", "content": full_response})
        st.rerun()

if user_prompt := st.chat_input("Ask me anything?"):
    if user_prompt.lower() == 'resume conversation':
        st.session_state.assistant.resume_conversation()
        user_prompt = None
        if len(st.session_state.messages) > 0 and st.session_state.messages[-1]['role'] == 'assistant':
            st.session_state.messages.pop(-1)
    else:
        with st.chat_message("user"):
            st.markdown(user_prompt)
        st.session_state.messages.append({"role": "user", "content": user_prompt})

    with st.chat_message("assistant"):
        full_response = st.session_state.assistant.get_assistant_response(user_prompt)
    
    st.session_state.messages.append({"role": "assistant", "content": full_response})
    st.rerun()
